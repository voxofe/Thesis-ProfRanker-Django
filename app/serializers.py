from rest_framework import serializers
from .models import User, Application, Paper, EmploymentCertificate

# Serializer for User
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id',
            'first_name',
            'last_name',
            'email',
            'mobile_number',
            'landline_number',
            'street_address',
            'city',
            'postal_code',
            'role',
            'gender',
        ]

class EmploymentCertificateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmploymentCertificate
        fields = ["id", "file"]

# Serializer for Application
class ApplicationSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    employment_certificates = EmploymentCertificateSerializer(many=True, read_only=True)
    
    class Meta:
        model = Application
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)

        file_fields = [
            "course_plan_document",
            "phd_document",
            "doatap_document",
            "military_obligations_document",
            "cv_document",
            "public_employee_permission_document",
            "not_participated_declaration_document",
            "eu_citizen_greek_language_certificate_document",
            "responsible_declaration_document",
        ]

        for field in file_fields:
            file_obj = getattr(instance, field)
            data[field] = file_obj.url if file_obj else None

        data["employment_certificates"] = [
            {
                "id": cert.id,
                "file": cert.file.url if cert.file else None,
            }
            for cert in instance.employment_certificates.all()
        ]

        return data

# Serializer for Paper
class PaperSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paper
        fields = ['type', 'paper_title', 'journal_conf_title', 'year', 'issn', 'country', 'quartile']
