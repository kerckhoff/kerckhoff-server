from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from kerckhoff.integrations.serializers import IntegrationSerializer
from .models import PackageSet, Package, PackageVersion, PackageItem
from kerckhoff.users.serializers import UserSerializer, SimpleUserSerializer

from taggit_serializer.serializers import TagListSerializerField, TaggitSerializer


class PackageSetSerializer(serializers.ModelSerializer):
    created_by = SimpleUserSerializer(read_only=True)

    class Meta:
        model = PackageSet
        fields = ("id", "slug", "metadata", "created_by", "created_at", "updated_at")
        read_only_fields = ("id", "created_by", "created_at", "updated_at")


class PackageSetDetailedSerializer(PackageSetSerializer):
    integrations = IntegrationSerializer(
        many=True, read_only=True, source="integration_set"
    )

    class Meta(PackageSetSerializer.Meta):
        fields = PackageSetSerializer.Meta.fields + ("integrations",)
        read_only_fields = PackageSetSerializer.Meta.read_only_fields + (
            "integrations",
        )


class PackageSerializer(TaggitSerializer, serializers.ModelSerializer):
    package_set = serializers.StringRelatedField()
    created_by = SimpleUserSerializer(read_only=True)
    latest_version = serializers.StringRelatedField()
    tags = TagListSerializerField()

    class Meta:
        model = Package
        fields = (
            "id",
            "slug",
            "package_set",
            "metadata",
            "cached",
            "state",
            "last_fetched_date",
            "created_by",
            "created_at",
            "updated_at",
            "tags",
            "latest_version",
        )
        read_only_fields = (
            "id",
            "package_set",
            "cached",
            "last_fetched_date",
            "created_by",
            "created_at",
            "updated_at",
            "latest_version",
        )
        validators = [
            UniqueTogetherValidator(
                queryset=Package.objects.all(), fields=("slug", "package_set")
            )
        ]


class PackageItemSerializer(TaggitSerializer, serializers.ModelSerializer):
    tags = TagListSerializerField()

    def to_representation(self, instance: PackageItem):
        instance = instance.refresh()
        return super().to_representation(instance)

    class Meta:
        model = PackageItem
        fields = ("id", "data_type", "data", "file_name", "mime_type", "tags")
        read_only_fields = ("id", "data_type")


class PackageVersionSerializer(serializers.ModelSerializer):
    version_description = serializers.CharField(required=True)
    created_by = SimpleUserSerializer(read_only=True)

    class Meta:
        model = PackageVersion
        fields = (
            "id",
            "id_num",
            "title",
            "package",
            "created_by",
            "version_description",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "id_num",
            "package",
            "created_by",
            "created_at",
            "updated_at",
        )


class PackageVersionWithItemsSerializer(PackageVersionSerializer):
    packageitem_set = PackageItemSerializer(many=True)

    class Meta(PackageVersionSerializer.Meta):
        fields = PackageVersionSerializer.Meta.fields + ("packageitem_set",)
        read_only_fields = PackageVersionSerializer.Meta.read_only_fields + (
            "packageitem_set",
        )


class CreatePackageVersionSerializer(PackageVersionSerializer):
    included_items = serializers.ListField(child=serializers.CharField())

    def create(self, validated_data):
        package: Package = self.context["package"]
        included_items = validated_data.pop("included_items")
        package_version = PackageVersion(**validated_data)
        pv = package.create_version(
            self.context["user"], package_version, included_items
        )
        return pv

    def validate(self, attrs):
        package: Package = self.context["package"]
        cached_titles = set([item["title"] for item in package.cached])
        included_titles = set(attrs["included_items"])

        if len(included_titles) == 0:
            raise serializers.ValidationError(
                "A version must include at least one item to be updated!"
            )

        nonexistent = included_titles - cached_titles
        if len(nonexistent) > 0:
            raise serializers.ValidationError(
                f"The following titles do not exist in cache, and cannot be included: {', '.join(nonexistent)}."
            )
        return attrs

    class Meta(PackageVersionSerializer.Meta):
        fields = PackageVersionSerializer.Meta.fields + ("included_items",)


class RetrievePackageSerializer(PackageSerializer):
    version_data = serializers.SerializerMethodField()

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if ret.get("version_data") is not None:
            ret["cached"] = None
        return ret

    def get_version_data(self, obj: Package):
        version_number = self.context["version_number"]
        package_version = obj.get_version(version_number)
        if package_version is not None:
            data = PackageVersionWithItemsSerializer(package_version).data
        else:
            data = None
        return data

    class Meta(PackageSerializer.Meta):
        fields = PackageSerializer.Meta.fields + ("version_data",)
        read_only_fields = PackageSerializer.Meta.read_only_fields + ("version_data",)
