from decimal import Decimal

from django.db import models
from django.conf import settings
from django.db.models import Avg
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible

from django.contrib.auth.models import User
try:
    from django.contrib.contenttypes.fields import GenericForeignKey
except:
    from django.contrib.contenttypes.generic import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

from .categories import RATING_CATEGORY_CHOICES
from .managers import OverallRatingManager

USER_MODEL = getattr(settings, 'AUTH_USER_MODEL', User)


class OverallRating(models.Model):

    object_id = models.IntegerField(db_index=True)
    content_type = models.ForeignKey(ContentType)
    content_object = GenericForeignKey()
    rating = models.DecimalField(decimal_places=1, max_digits=6, null=True)
    category = models.IntegerField(null=True, choices=RATING_CATEGORY_CHOICES)

    objects = OverallRatingManager()

    class Meta:
        unique_together = [
            ("object_id", "content_type", "category"),
        ]

    def update(self):
        r = Rating.objects.filter(overall_rating=self).aggregate(r=Avg("rating"))["r"] or 0
        self.rating = Decimal(str(r))
        self.save()


@python_2_unicode_compatible
class Rating(models.Model):
    overall_rating = models.ForeignKey(OverallRating, null=True, related_name="ratings")
    object_id = models.IntegerField(db_index=True)
    content_type = models.ForeignKey(ContentType)
    content_object = GenericForeignKey()
    user = models.ForeignKey(USER_MODEL)
    rating = models.IntegerField()
    timestamp = models.DateTimeField(default=timezone.now)
    category = models.IntegerField(null=True, choices=RATING_CATEGORY_CHOICES)

    def clear(self):
        overall = self.overall_rating
        self.delete()
        overall.update()
        return overall.rating

    @classmethod
    def update(cls, rating_object, user, rating, category=None):
        # @@@ Still doing too much in this method
        ct = ContentType.objects.get_for_model(rating_object)
        try:
            rating_obj = cls.objects.get(
                object_id=rating_object.pk,
                content_type=ct,
                user=user,
                category=category
            )
        except cls.DoesNotExist:
            rating_obj = None

        if rating_obj and rating == 0:
            return rating_obj.clear()

        if rating_obj is None:
            rating_obj = cls.objects.create(
                object_id=rating_object.pk,
                content_type=ct,
                user=user,
                category=category,
                rating=rating
            )
        overall, _ = OverallRating.objects.get_or_create(
            object_id=rating_object.pk,
            content_type=ct,
            category=category
        )
        rating_obj.overall_rating = overall
        rating_obj.rating = rating
        rating_obj.save()
        overall.update()
        return overall.rating

    class Meta:
        unique_together = [
            ("object_id", "content_type", "user", "category"),
        ]

    def __str__(self):
        return str(self.rating)
