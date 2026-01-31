import uuid

from rest_framework import serializers

from base.models import (Agrement, Category, Change, Client, Domain, Kind, Lot,
                         Meeting, Mode, Procedure, Qualif, RelAgrementLot,
                         RelDomainTender, RelQualifLot, Sample, Tender, Visit)
from scraper import helper


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'label']


class ChangeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Change
        fields = ['id', 'tender', 'reported', 'changes']


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ['id', 'short', 'name', 'ministery']


class KindSerializer(serializers.ModelSerializer):
    class Meta:
        model = Kind
        fields = ['id', 'short', 'name']


# class ContactSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Contact
#         fields = [
#             'id', 'when', 'ua', 'ip', 'email', 'phone', 'title',
#             'message', 'method', 'newsletter', 'promos', 'comment',
#             'actions', 'solved', 'file', 'utilizer'
#             ]


class DomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = Domain
        fields = ['id', 'short', 'name']


# class DownloadSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Download
#         fields = [
#             'id', 'when', 'ua', 'ip', 'tender', 'bytes_media', 'utilizer'
#             ]


# class FavoSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Favo
#         fields = [
#             'id', 'when', 'ua', 'ip', 'tender', 'comment', 'utilizer'
#             ]


class AgrementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agrement
        fields = ['id', 'short', 'name']


class QualifSerializer(serializers.ModelSerializer):
    class Meta:
        model = Qualif
        fields = ['id', 'short', 'name', 'domain', 'classe']


class ModeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mode
        fields = ['id', 'short', 'name']


class ProcedureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Procedure
        fields = ['id', 'short', 'name']


class SampleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sample
        fields = ['id', 'when', 'description', 'lot']


class MeetingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Meeting
        fields = ['id', 'when', 'description', 'lot']


class VisitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Visit
        fields = ['id', 'when', 'description', 'lot']


class LotSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    agrements = AgrementSerializer(many=True, read_only=True)
    qualifs = QualifSerializer(many=True, read_only=True)
    samples = SampleSerializer(many=True, read_only=True)
    meetings = MeetingSerializer(many=True, read_only=True)
    visits = VisitSerializer(many=True, read_only=True)
    
    class Meta:
        model = Lot
        fields = [
            'id', 'number', 'title', 'description', 'estimate', 'bond', 
            'reserved', 'variant', 'category', 'tender',
            'agrements', 'qualifs', 'samples', 'meetings', 'visits'
        ]


class TenderSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    client = ClientSerializer(read_only=True)
    kind = KindSerializer(read_only=True)
    mode = ModeSerializer(read_only=True)
    procedure = ProcedureSerializer(read_only=True)
    domains = DomainSerializer(many=True, read_only=True)
    lots = LotSerializer(many=True, read_only=True)
    
    class Meta:
        model = Tender
        fields = [
            'id', 'chrono', 'title', 'reference', 'published', 'deadline', 
            'lots_count', 'estimate', 'bond', 'plans_price', 'reserved', 
            'variant', 'location', 'ebid', 'esign', 'size_read', 
            'size_bytes', 'address_withdrawal', 'address_bidding', 
            'address_opening', 'contact_name', 'contact_phone', 'contact_email', 
            'contact_fax', 'created', 'updated', 'cancelled', 'link', 'acronym', 
            'category', 'mode', 'procedure', 'client', 'kind', 'domains', 'lots'
        ]


    # def update(self, instance, validated_data):
    #     changes = {}
    #     for field, new_value in validated_data.items():
    #         old_value = getattr(instance, field)
    #         if old_value != new_value:
    #             changes[field] = {
    #                 'old_value': str(old_value),
    #                 'new_value': str(new_value)
    #             }
    #     if changes:
    #         change = Change(tender=instance, changes=changes)
    #         change.save()
    #         log_message = f"Tender {instance.chrono} updated. Changes saved."
    #         helper.printMessage('INFO', 'serializer.TenderSerializer', log_message, 2, 3)

    #     return super().update(instance, validated_data)


class RelAgrementLotSerializer(serializers.ModelSerializer):
    agrement = AgrementSerializer(read_only=True)
    lot = LotSerializer(read_only=True)
    
    class Meta:
        model = RelAgrementLot
        fields = ['agrement', 'lot']


class RelDomainTenderSerializer(serializers.ModelSerializer):
    domain = DomainSerializer(read_only=True)
    tender = TenderSerializer(read_only=True)
    
    class Meta:
        model = RelDomainTender
        fields = ['domain', 'tender']


class RelQualifLotSerializer(serializers.ModelSerializer):
    qualif = QualifSerializer(read_only=True)
    lot = LotSerializer(read_only=True)
    
    class Meta:
        model = RelQualifLot
        fields = ['qualif', 'lot']