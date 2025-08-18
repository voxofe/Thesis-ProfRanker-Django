from rest_framework import serializers
from .models import User, Application, Paper

# Serializer for User
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email', 'role']

# Serializer for Application
class ApplicationSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Application
        fields = '__all__'

    def to_representation(self, instance):
        """Ensure FileFields return a string URL instead of a file object."""
        data = super().to_representation(instance)
        
        # Convert FileFields to their URL or name
        file_fields = [
            "course_plan_document",
            "phd_document",
            "doatap_document",
            "military_obligations_document",
            "cv_document"
        ]

        for field in file_fields:
            file_obj = getattr(instance, field)
            data[field] = file_obj.url if file_obj else None  # Ensure we return URL, not object

        return data

# Serializer for Paper
class PaperSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paper
        fields = ['type', 'paper_title', 'journal_conf_title', 'year', 'issn', 'country', 'quartile']
