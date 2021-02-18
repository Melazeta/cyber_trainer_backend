import math
import itertools

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from trainer import sr
from trainer.models import LevelScore
from trainer.serializers import LevelScoreSerializer


class PlayerStats(APIView):
    """
    Provides player's statistics as scores and errors for each case
    """
    def get(self, request, format=None):
        player_levels = LevelScore.objects.filter(
            user=request.user.id
        )

        return Response(LevelScoreSerializer(player_levels, many=True).data)


class Cases(APIView):
    """
    Return the solved cases with the player statistics and the next case
    """
    permission_classes = (IsAuthenticated,)

    @staticmethod
    def genLabels(text, labels, sep="|"):
        # Example of usage => genLabels(emails["EL0001"]["text"], emails["EL0001"]["labels"])
        # Prepare labels list for the frontend
        _labels = []
        for t in text.split(sep):
            if labels.get(t):
                _labels.append({
                    "text": labels[t].get("content"),
                    "relevant": labels[t].get("relevant")
                })
            else:
                _labels.append({
                    "text": t
                })
        
        return _labels

    @staticmethod
    def normalize_errors(errors):
        # If vectors is null, gives same probability for each category
        if not any(errors):
            return [1/len(errors) for x in errors]

        # If there are not null values, return the probability vector
        if all(errors):
            tmp = [math.log(1 + x) for x in errors]
        else:
            # Get minimum errors number (not null)
            min_e = min([x for x in errors if x])
            tmp = [math.log(1 + x) if x else math.log(1 + min_e / 2) for x in errors]

        return [x / sum(tmp) for x in tmp]

    @staticmethod
    def time_normalized(t, t_min, t_max, t_norm_min=0.8, t_norm_max=1.0):
        """
        Normalize player time spent to pass the level
        """
        if t < t_min:
            return t_norm_max

        if t > t_max:
            return t_norm_min

        return t_norm_max - (t - t_min) / (t_max  - t_min) * (t_norm_max - t_norm_min)

    @staticmethod
    def compute_score(stats):
        MAX_TIME = 90
        # Compute the right labels on total labels
        score = stats["right_labels"] / (stats["right_labels"] + stats["email_errors"] + \
            stats["conversation_errors"] + stats["file_errors"] + stats["site_errors"])

        # TODO Normalize score with the scores of all players who solved the case

        # Moltiply the final score for the normalized time spent
        # TODO add check if player time spent is equal or higher of max time
        return score * (math.log(MAX_TIME - stats["time_spent"]) / math.log(MAX_TIME))

    def get(self, request, format=None):
        # Retrive player levels stats for all solved cases
        player_levels = LevelScore.objects.filter(
            user=request.user.id
        )
        cases = {
            "solved_cases": [],
        }
        # Add all solved cases with score
        for level_stat in player_levels:
            cases["solved_cases"].append({
                "player_stats": LevelScoreSerializer(player_levels).data,   # Player stats (score)
                "case_details": sr.get("cases").get(level_stat.case)        # Case (level) details
            })
            # Compute the dynamic score
            cases["solved_cases"][-1]["player_stats"] = Cases.compute_score(
                cases["solved_cases"][-1]["player_stats"]
            )
            # Move case id from "player stats" to "case details"
            cases["solved_cases"][-1]["case_details"]["case_id"] = \
                cases["solved_cases"][-1]["player_stats"]["case"]

        # Add next case and locked case (the next of the next case)
        if cases["solved_cases"]:
            # Compute the cases id to retrive them
            next_case_id = int(cases["solved_cases"][-1]["case_details"]["case_id"][2:]) + 1
            id_str = "CE%04d" % next_case_id
            cases["next_case"] = sr.get("cases").get(id_str)
            cases["next_case"]["case_id"] = id_str

            id_str = "CE%04d" % (next_case_id + 1)
            cases["locked_case"] = sr.get("cases").get(id_str)
            cases["locked_case"]["case_id"] = id_str
        else:
            cases["next_case"] = sr.get("cases").get("CE0001")
            cases["next_case"]["case_id"] = "CE0001"

            cases["locked_case"] = sr.get("cases").get("CE0002")
            cases["locked_case"]["case_id"] = "CE0002"

        return Response(cases)

    def post(self, request, format=None):
        # TODO Load case data only one time (it will never change during the execution)
        # Retrive case from settings
        case = sr.get("cases").get(request.data["case_id"])
        if not case:
            return Response(
                data={"detail": "Invalid case id"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Retrive case characters
        characters = {}
        for character_id in case["characters"]:
            characters[character_id] = sr.get("characters").get(character_id)
        
        case["characters"] = characters

        # Create links between characters from conversations and emails
        contacts = {}
        # Create for each character id (key) a list of calls, chats and emails IDs
        for character_id, character in case["characters"].items():
            contacts[character_id] = [call["call_id"] for call in character["calls"]] + \
                [chat["chat_id"] for chat in character["chats"]] + \
                [email["email_id"] for email in character["emails"]]

        # Add a link between two characters if they have at least one contact in common
        # the keys of the links are the tuples of two characters (for each character combination)
        # and the value in a boolean represent the connection between them
        links = {x: any(set(contacts[x[0]]) & set(contacts[x[1]])) \
            for x in itertools.combinations(case["characters"].keys(), 2)}

        case["links"] = [{ "source": k[0], "target": k[1] } for k, v in links.items() if v ]

        # Add all steps and labels of the case (ex. case["emails"], case["conversations"], ...)
        case["sections"] = {
            "emails": {},
            "sites": {},
            "chats": {},
            "calls": {}
        }
        # Iterate on each employer
        for employer_id in case["characters"].keys():
            # Iterate on each employer section (emails, chats, calls, ...)
            for section in case["sections"].keys():
                # Iterate on each section element
                for element in case["characters"][employer_id][section]:
                    element_id = section[:-1] + "_id"
                    # Retrive element content from Settings Reader
                    case["sections"][section][element[element_id]] = sr.get(
                        section).get(element[element_id])

        # Extract all files id from emails case attachments and downloadble site files
        files_id = set(*[email["attachments"] for email in case["sections"]["emails"].values() if email.get("attachments") and len(email["attachments"])]) \
            | set(*[site["downloadble"] for site in case["sections"]["sites"].values() if site.get("downloadble") and len(site["downloadble"])])

        # Add to case section all files data
        case["sections"]["files"] = {}
        for file_id in files_id:
            case["sections"]["files"][file_id] = sr.get("files").get(file_id)

        return Response(case)
