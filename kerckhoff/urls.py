from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path, reverse_lazy
from django.views.generic.base import RedirectView
from rest_framework.authtoken import views
from rest_framework.routers import DefaultRouter
from rest_framework.documentation import include_docs_urls
from rest_framework.permissions import AllowAny
from rest_framework_nested.routers import NestedSimpleRouter
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from .users.urls import urlpatterns as auth_urlpatterns
from .users.views import UserCreateViewSet, UserViewSet
from .packages.views import (
    PackageSetViewSet,
    PackageSetCreateAndListViewSet,
    PackageViewSet,
    PackageCreateAndListViewSet,
)
from .comments.views import CommentViewSet
from .integrations.views import IntegrationOAuthView

router = DefaultRouter()
router.register(r"users", UserViewSet)
router.register(r"users", UserCreateViewSet)
router.register(r"package-sets", PackageSetViewSet)
router.register(r"package-sets", PackageSetCreateAndListViewSet)

package_set_router = NestedSimpleRouter(router, r"package-sets", lookup="package_set")
package_set_router.register(
    r"packages", PackageViewSet, base_name="package-sets_packages"
)
package_set_router.register(
    r"packages", PackageCreateAndListViewSet, base_name="package-sets_packages"
)

package_router = NestedSimpleRouter(package_set_router, r"packages", lookup="package")
package_router.register(r"comments", CommentViewSet, base_name="comments")

schema_view = get_schema_view(
    openapi.Info(
        title="Kerckhoff API", default_version="v1", description="The Kerckhoff API"
    ),
    public=True,
    permission_classes=(AllowAny,),
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "api/v1/docs-old/",
        include_docs_urls(
            title="Kerckhoff REST API (v1)", permission_classes=[AllowAny]
        ),
    ),
    re_path(
        r"^api/v1/docs/swagger(?P<format>\.json|\.yaml)$",
        schema_view.without_ui(cache_timeout=0),
        name="schema-json",
    ),
    re_path(
        r"^api/v1/docs/swagger-ui/$",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    re_path(
        r"^api/v1/docs/$",
        schema_view.with_ui("redoc", cache_timeout=0),
        name="schema-redoc",
    ),
    path("api/v1/", include(router.urls)),
    path("api/v1/", include(package_set_router.urls)),
    path("api/v1/", include(package_router.urls)),
    path("api/v1/integrations/", IntegrationOAuthView.as_view()),
    path("api-oauth/", include(auth_urlpatterns)),
    path("api-token-auth/", views.obtain_auth_token),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    # the 'api-root' from django rest-frameworks default router
    # http://www.django-rest-framework.org/api-guide/routers/#defaultrouter
    re_path(r"^$", RedirectView.as_view(url=reverse_lazy("api-root"), permanent=False)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
