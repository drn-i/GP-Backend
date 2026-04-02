from rest_framework import serializers

class WESADFeaturesSerializer(serializers.Serializer):
    """Validates the 27 nested features from the WESAD dataset"""
    hr_mean = serializers.FloatField()
    hr_std = serializers.FloatField()
    hr_min = serializers.FloatField()
    hr_max = serializers.FloatField()
    hr_range = serializers.FloatField()
    
    eda_mean = serializers.FloatField()
    eda_std = serializers.FloatField()
    eda_min = serializers.FloatField()
    eda_max = serializers.FloatField()
    eda_range = serializers.FloatField()
    
    bvp_mean = serializers.FloatField()
    bvp_std = serializers.FloatField()
    bvp_min = serializers.FloatField()
    bvp_max = serializers.FloatField()
    bvp_range = serializers.FloatField()
    
    ibi_mean = serializers.FloatField()
    ibi_std = serializers.FloatField()
    ibi_min = serializers.FloatField()
    ibi_max = serializers.FloatField()
    ibi_range = serializers.FloatField()
    ibi_rmssd = serializers.FloatField()
    
    acc_mag_mean = serializers.FloatField()
    acc_mag_std = serializers.FloatField()
    acc_mag_min = serializers.FloatField()
    acc_mag_max = serializers.FloatField()
    acc_mag_range = serializers.FloatField()
    acc_activity = serializers.FloatField()


class RiskResultSerializer(serializers.Serializer):
    """Validates the incoming JSON payload before saving to MongoDB"""
    user_id = serializers.CharField(max_length=50)
    timestamp = serializers.DateTimeField()
    features = WESADFeaturesSerializer() 
    risk_level = serializers.CharField(max_length=20)
      
      
    confidence = serializers.FloatField(required=False)
    summary = serializers.CharField(required=False, allow_blank=True)
    recommendation = serializers.CharField(required=False, allow_blank=True)

# Segment 1 Aligned Features Serializer with EmotiBit Features
class Segment1AlignedFeaturesSerializer(serializers.Serializer):
    EDA_mean = serializers.FloatField(allow_null=True, required=False)
    EDA_std = serializers.FloatField(allow_null=True, required=False)
    EDA_min = serializers.FloatField(allow_null=True, required=False)
    EDA_max = serializers.FloatField(allow_null=True, required=False)

    BVP_std = serializers.FloatField(allow_null=True, required=False)
    BVP_peak_freq = serializers.FloatField(allow_null=True, required=False)

    TEMP_mean = serializers.FloatField(allow_null=True, required=False)
    TEMP_std = serializers.FloatField(allow_null=True, required=False)
    TEMP_slope = serializers.FloatField(allow_null=True, required=False)

    ACC_x_std = serializers.FloatField(allow_null=True, required=False)
    ACC_y_std = serializers.FloatField(allow_null=True, required=False)
    ACC_z_std = serializers.FloatField(allow_null=True, required=False)

    net_acc_mean = serializers.FloatField(allow_null=True, required=False)
    net_acc_std = serializers.FloatField(allow_null=True, required=False)
    net_acc_max = serializers.FloatField(allow_null=True, required=False)
    net_acc_min = serializers.FloatField(allow_null=True, required=False)

    age = serializers.FloatField(allow_null=True, required=False)
    height = serializers.FloatField(allow_null=True, required=False)
    weight = serializers.FloatField(allow_null=True, required=False)


class Segment1LLMResultSerializer(serializers.Serializer):
    stress_detected = serializers.BooleanField()
    confidence = serializers.FloatField(required=False, allow_null=True)
    reasoning = serializers.CharField(required=False, allow_blank=True)
    contributing_signals = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
    summary = serializers.CharField(required=False, allow_blank=True)


class Segment1RunpodSerializer(serializers.Serializer):
    request_id = serializers.CharField(required=False, allow_blank=True)
    status = serializers.CharField(required=False, allow_blank=True)
    delay_time_ms = serializers.IntegerField(required=False, allow_null=True)
    execution_time_ms = serializers.IntegerField(required=False, allow_null=True)
    worker_id = serializers.CharField(required=False, allow_blank=True)
    endpoint_id = serializers.CharField(required=False, allow_blank=True)


class Segment1ResultSerializer(serializers.Serializer):
    user_id = serializers.CharField(max_length=128)
    timestamp = serializers.DateTimeField()
    window = serializers.DictField()
    feature_alignment_version = serializers.CharField(required=False, allow_blank=True)
    prompt_source = serializers.CharField(required=False, allow_blank=True)
    prompt_version = serializers.CharField(required=False, allow_blank=True)
    features_aligned = Segment1AlignedFeaturesSerializer(required=False)
    llm_result = Segment1LLMResultSerializer()
    runpod = Segment1RunpodSerializer(required=False)