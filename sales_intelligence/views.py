from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .crm_adapters.krishna.lead import (
    get_krishna_lead_features,
)

from .lead_scoring.scoring_engine import (
    score_leads,
)

from .lead_scoring.scoring_report import (
    create_scoring_report,
)

from .conversion_prediction.pipeline import (
    train_conversion_pipeline,
    predict_conversion_pipeline,
)

from .development_data.synthetic.lead_conversion_training_data import (
    SYNTHETIC_LEAD_CONVERSION_DATA,
)


class LeadScoringView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        features = get_krishna_lead_features()

        scored_leads = score_leads(
            features
        )

        report = create_scoring_report(
            scored_leads
        )

        return Response(report)


class LeadConversionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        # -----------------------------------------
        # 1. Get synthetic development data
        # -----------------------------------------

        training_records = (
            SYNTHETIC_LEAD_CONVERSION_DATA
        )

        # -----------------------------------------
        # 2. Separate features and targets
        # -----------------------------------------

        training_features = []

        training_outcomes = []

        for record in training_records:

            features = {
                key: value
                for key, value in record.items()
                if key != "converted"
            }

            training_features.append(
                features
            )

            training_outcomes.append({
                "converted": record["converted"]
            })

        # -----------------------------------------
        # 3. Train conversion model
        # -----------------------------------------

        model = train_conversion_pipeline(
            training_features,
            training_outcomes,
        )

        # -----------------------------------------
        # 4. Get actual Krishna CRM leads
        # -----------------------------------------

        krishna_features = (
            get_krishna_lead_features()
        )

        # -----------------------------------------
        # 5. Generate predictions
        # -----------------------------------------

        predictions = (
            predict_conversion_pipeline(
                model,
                krishna_features,
            )
        )

        # -----------------------------------------
        # 6. Return API response
        # -----------------------------------------

        return Response({
            "model": "Logistic Regression",

            "development_data": {
                "records": len(
                    training_records
                ),
                "description": (
                    "Synthetic development data "
                    "based on Krishna CRM feature "
                    "patterns."
                ),
            },

            "crm": "Krishna CRM",

            "total_leads": len(
                predictions
            ),

            "predictions": predictions,
        })