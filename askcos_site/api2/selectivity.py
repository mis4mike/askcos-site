from rdkit import Chem
from rest_framework import serializers

from askcos_site.askcos_celery.siteselectivity.sites_worker import get_sites
from .celery import CeleryTaskAPIView


class SelectivitySerializer(serializers.Serializer):
    """Serializer for site selectivity task parameters."""
    smiles = serializers.CharField()
    async = serializers.BooleanField(default=True)

    def validate_smiles(self, value):
        """Verify that the requested smiles is valid."""
        if not Chem.MolFromSmiles(value):
            raise serializers.ValidationError('Cannot parse smiles with rdkit.')
        return value


class SelectivityAPIView(CeleryTaskAPIView):
    """
    API endpoint for site selectivity prediction task.

    Method: POST

    Parameters:

    - `smiles` (str): SMILES string of target
    - `async` (bool, optional): whether to directly return celery task id instead of waiting for result

    Returns:

    - `output`: site selectivity prediction
    """

    serializer_class = SelectivitySerializer

    def execute(self, data):
        """
        Execute site selectivity task and return celery result object.
        """
        result = get_sites.delay(data['smiles'])
        return result


selectivity = SelectivityAPIView.as_view()
