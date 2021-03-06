from rest_framework import mixins, viewsets, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.serializers import Serializer
from rest_framework.response import Response

from kerckhoff.integrations.serializers import IntegrationSerializer
from .tasks import sync_gdrive_task

from .models import PackageSet, Package
from .serializers import (
    PackageSetSerializer,
    PackageSerializer,
    RetrievePackageSerializer,
    PackageVersionSerializer,
    CreatePackageVersionSerializer,
    PackageSetDetailedSerializer,
)


slug_with_dots = "[-a-zA-Z0-9_.&]+"


class PackageSetViewSet(
    mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet
):
    """
    Updates and retrieves individual Package Sets
    """

    queryset = PackageSet.objects.all()
    serializer_class = PackageSetDetailedSerializer
    permission_classes = (IsAuthenticated,)
    lookup_field = "slug"
    lookup_value_regex = slug_with_dots

    @action(methods=["post"], detail=True, serializer_class=Serializer)
    def sync_gdrive(self, request, slug):
        """
        Imports all packages from the Google Drive folder of a package set
        """
        response = sync_gdrive_task(slug)
        return Response(response)

    @action(methods=["post"], detail=True, serializer_class=Serializer)
    def async_sync_gdrive(self, request, slug):
        task = sync_gdrive_task.delay(slug)
        return Response({"id": task.id})

    @action(methods=["post"], detail=True, serializer_class=IntegrationSerializer)
    def integration(self, request, slug):
        package_set: PackageSet = self.get_object()
        new_integration = IntegrationSerializer(data=request.data)
        new_integration.is_valid(raise_exception=True)
        new_integration.save(created_by=request.user, package_set=package_set)
        return Response(new_integration.data)


class PackageSetCreateAndListViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet
):
    """
    Creates and lists new Package Sets
    """

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    queryset = PackageSet.objects.all()
    serializer_class = PackageSetSerializer
    permission_classes = (IsAuthenticated,)
    lookup_field = "slug"
    lookup_value_regex = slug_with_dots
    filter_backends = (filters.OrderingFilter,)
    ordering_fields = ("slug", "last_fetched_date", "created_at", "updated_at")


class PackageViewSet(
    mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet
):
    """
    Updates and retrieves packages
    """
    def get_queryset(self):
        return Package.objects.filter(package_set__slug=self.kwargs["package_set_slug"])

    serializer_class = PackageSerializer
    permission_classes = (IsAuthenticated,)
    lookup_field = "slug"
    lookup_value_regex = slug_with_dots

    @action(methods=["post"], detail=True, serializer_class=Serializer)
    def preview(self, request, **kwargs):
        package = self.get_object()
        package.fetch_cache()
        serializer = PackageSerializer(package, many=False)
        return Response(serializer.data)

    @action(methods=["post"], detail=True, serializer_class=Serializer)
    def publish(self, request, **kwargs):
        package = self.get_object()
        package.publish()
        return Response(status=200)

    @action(
        methods=["post"], detail=True, serializer_class=CreatePackageVersionSerializer
    )
    def snapshot(self, request, **kwargs):
        package: Package = self.get_object()
        package_version = CreatePackageVersionSerializer(
            data=request.data, context={"package": package, "user": request.user}
        )
        package_version.is_valid(True)
        updated_pv = package_version.save()
        return Response(PackageVersionSerializer(updated_pv).data)

    @action(methods=["get"], detail=True)
    def versions(self, request, **kwargs):
        package: Package = self.get_object()
        serializer = PackageVersionSerializer(package.get_all_versions(), many=True)
        return Response({"results": serializer.data})

    def retrieve(self, request, **kwargs):
        package = self.get_object()
        version_number = request.query_params.get("version", -1)
        serializer = RetrievePackageSerializer(
            package, context={"version_number": version_number}
        )
        response = serializer.data
        return Response(response)


class PackageCreateAndListViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet
):
    """
    Creates and lists packages
    """

    def get_queryset(self):
        return Package.objects.filter(package_set__slug=self.kwargs["package_set_slug"])

    def perform_create(self, serializer):
        package_set = PackageSet.objects.get(slug=self.kwargs["package_set_slug"])
        serializer.save(created_by=self.request.user, package_set=package_set)

    serializer_class = PackageSerializer
    permission_classes = (IsAuthenticated,)
    lookup_field = "slug"
    lookup_value_regex = slug_with_dots
    filter_backends = (filters.OrderingFilter,)
    ordering_fields = ("slug", "last_fetched_date", "created_at", "updated_at")
