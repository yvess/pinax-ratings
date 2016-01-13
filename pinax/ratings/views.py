from django.conf import settings
from django.http import HttpResponseForbidden
try:  # JsonResponse is only available in Django > 1.7
    from django.http import JsonResponse
except ImportError:
    from django.utils import simplejson
    from django.http import HttpResponse

    class JsonResponse(HttpResponse):
        def __init__(self, content, mimetype='application/json',
                     status=None, content_type=None):
            super(JsonResponse, self).__init__(
                content=simplejson.dumps(content), mimetype=mimetype,
                status=status, content_type=content_type,
            )

from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from django.contrib.contenttypes.models import ContentType

try:
    from account.decorators import login_required
except ImportError:
    from django.contrib.auth.decorators import login_required

from .categories import category_value
from .models import Rating


NUM_OF_RATINGS = getattr(settings, "PINAX_RATINGS_NUM_OF_RATINGS", 5)
RATINGS_USER = getattr(settings, "PINAX_RATINGS_USER", None)
RATINGS_RATING_OBJECT = getattr(settings, "PINAX_RATINGS_RATING_OBJECT", None)
RATINGS_AUTO_OVERALL_UPDATE = getattr(settings, "PINAX_RATINGS_AUTO_OVERALL_UPDATE", True)


@require_POST
#@login_required
def rate(request, content_type_id, object_id):
    ct = get_object_or_404(ContentType, pk=content_type_id)
    obj = get_object_or_404(ct.model_class(), pk=object_id)
    rating_input = int(request.POST.get("rating"))
    category = request.POST.get("category")
    cat_choice = category_value(obj, category)

    # Check for errors and bail early
    if category is not None and cat_choice is None:
        return HttpResponseForbidden(
            "Invalid category. It must match a preconfigured setting"
        )
    if rating_input not in range(NUM_OF_RATINGS + 1):
        return HttpResponseForbidden(
            "Invalid rating. It must be a value between 0 and %s" % NUM_OF_RATINGS
        )

    data = {
        "user_rating": rating_input,
        "overall_rating": 0,
        "category": category
    }

    user = getattr(obj, RATINGS_USER) if RATINGS_USER else request.user
    rating_object = getattr(obj, RATINGS_RATING_OBJECT) if RATINGS_RATING_OBJECT else obj

    if RATINGS_AUTO_OVERALL_UPDATE:
        data["overall_rating"] = str(Rating.update(
            rating_object=rating_object,
            user=user,
            category=cat_choice,
            rating=rating_input,
        ))

    return JsonResponse(data)
