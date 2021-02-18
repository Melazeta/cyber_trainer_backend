from django.db import models
from django.core.validators import MinValueValidator
from django.contrib.auth.models import User


# TODO Create view (better if merged with user registration)
class Player(User):
    """
    Extend simple user class by adding extra information for statistical scopes
    """
    company = models.CharField(max_length=75, null=False)
    job = models.CharField(max_length=50, null=False)
    born = models.DateField(null=False)


class LevelScore(models.Model):
    """
    Contains the player score in a case

    Store each played and passed level
    """
    user = models.ForeignKey(
        Player,
        related_name="player_stats",
        on_delete=models.CASCADE
    )
    case = models.CharField(max_length=10)
    # Time spent by the player to resolve the case (level)
    time_spent = models.IntegerField(validators=(MinValueValidator(0),), null=False)
    # Count the number of right labels (detected by the player)
    right_labels = models.IntegerField(validators=(MinValueValidator(0),), null=False)

    # Datetime when level has been passed
    played = models.DateTimeField(auto_created=True)

    # Store missed label by tipology (useful for machine learning analysis and game experience)
    email_errors = models.SmallIntegerField(default=0, validators=(MinValueValidator(0),))
    file_errors = models.SmallIntegerField(default=0, validators=(MinValueValidator(0),))
    conversation_errors = models.SmallIntegerField(default=0, validators=(MinValueValidator(0),))
    site_errors = models.SmallIntegerField(default=0, validators=(MinValueValidator(0),))

    class Meta:
        ordering = ("user", "case")
        unique_together = ("user", "case")
