from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    MONGODB_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "kisansathi"
    MONGODB_CONNECT_TIMEOUT_MS: int = 2000
    FARM_STATE_DB_DIR: str = "data/farm_state"
    FARM_STATE_UPLOAD_DIR: str = "data/farm_uploads"
    # The Tomato simulator is disabled unless a local/demo operator opts in.
    TOMATO_DEMO_ENABLED: bool = False
    # JSON map keyed by device ID. Each value has a provisioned ``token``,
    # ``farmer_id`` and optional ``field_ids`` list. Keep secrets out of git.
    DEVICE_INGESTION_CREDENTIALS_JSON: str = "{}"
    WEATHER_PROVIDER: str = "open_meteo"
    WEATHER_TIMEOUT_SECONDS: float = 8.0
    WEATHER_CACHE_SECONDS: int = 900
    MAX_DIAGNOSIS_IMAGE_BYTES: int = 8 * 1024 * 1024
    MAX_VOICE_AUDIO_BYTES: int = 10 * 1024 * 1024
    DIAGNOSIS_PROVIDER: str = "unconfigured"
    # Hosted crop-health settings. A blank key or base URL deliberately leaves
    # the provider unavailable instead of attempting an undocumented endpoint.
    KINDWISE_CROP_HEALTH_API_KEY: str = ""
    KINDWISE_CROP_HEALTH_BASE_URL: str = ""
    KINDWISE_CROP_HEALTH_IDENTIFICATION_PATH: str = "/api/v1/identification"
    KINDWISE_CROP_HEALTH_TIMEOUT_SECONDS: float = 20.0
    KINDWISE_CROP_HEALTH_LANGUAGE: str = "en"
    KINDWISE_CROP_HEALTH_MAX_IMAGES: int = 3
    # Local crop-health inference is opt-in. The checked-in configuration never
    # silently enables a demo checkpoint as a production diagnostic service.
    CROP_HEALTH_ROUTER_MODEL_PATH: str = ""
    CROP_HEALTH_SPECIALIST_MODELS_JSON: str = "{}"
    CROP_HEALTH_MIN_DISEASE_SCORE: float = 0.70
    CROP_HEALTH_MIN_DISEASE_MARGIN: float = 0.15
    # The registry is an opt-in prototype bundle. Paths are supplied by the
    # model-bundle setup script so a normal desktop launch stays lightweight.
    CROP_HEALTH_MODEL_REGISTRY_PATH: str = ""
    CROP_HEALTH_MODEL_ROOT: str = ""
    CROP_HEALTH_MODEL_IDS: str = ""
    CROP_HEALTH_MODEL_MAX_COUNT: int = 4
    CROP_HEALTH_TFLITE_MODEL_PATH: str = ""
    CROP_HEALTH_TFLITE_LABELS_PATH: str = ""
    CROP_HEALTH_TFLITE_CROP: str = "tomato"
    # A completed local diagnosis requires a versioned release manifest which
    # binds the configured model/labels to approved field and OOD evidence.
    # An empty path is intentionally review-only.
    CROP_HEALTH_TFLITE_RELEASE_MANIFEST_PATH: str = ""
    # A separate router is optional.  It may only suggest a crop; the farmer
    # must still confirm it before a crop-specific specialist is invoked.
    CROP_HEALTH_TFLITE_ROUTER_MODEL_PATH: str = ""
    CROP_HEALTH_TFLITE_ROUTER_LABELS_PATH: str = ""
    CROP_HEALTH_MIN_CROP_SCORE: float = 0.80
    CROP_HEALTH_MIN_CROP_MARGIN: float = 0.15
    ADVISOR_PROVIDER: str = "unconfigured"
    VOICE_PROVIDER: str = "unconfigured"
    SARVAM_API_KEY: str = ""
    SARVAM_BASE_URL: str = "https://api.sarvam.ai"
    SARVAM_TIMEOUT_SECONDS: float = 30.0
    SARVAM_STT_MODEL: str = "saaras:v3"
    SARVAM_STT_MODE: str = "transcribe"
    SARVAM_STT_LANGUAGE_CODE: str = "unknown"
    SARVAM_TTS_MODEL: str = "bulbul:v3"
    SARVAM_TTS_SPEAKER: str = "shubh"
    SARVAM_TTS_PACE: float = 1.0
    SARVAM_TTS_SPEECH_SAMPLE_RATE: int = 24000
    SARVAM_TTS_CODEC: str = "wav"
    SARVAM_TRANSLATE_MODEL: str = "mayura:v1"
    DATA_GOV_IN_API_KEY: str = ""
    UNIVERSAL_DATA_HTTP_TIMEOUT_SECONDS: float = 30.0
    UNIVERSAL_DATA_PAGE_SIZE: int = 1000
    UNIVERSAL_DATA_MAX_MARKET_RECORDS: int = 0
    SCRAPER_WEBHOOK_TOKEN: str = ""
    MSP_MARKETING_YEAR: str = "2026-27"
    MSP_KHARIF_URL: str = "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2260618&lang=2&reg=48"
    MSP_RABI_URL: str = "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2173567&lang=35&reg=38"
    MARKETPLACE_DIRECTORY_SOURCES_JSON: str = '[{"url":"https://agriexchange.apeda.gov.in/AgriDirectory/Exporter/Exporters","name":"APEDA registered exporters","listing_type":"exporter","adapter":"apeda_exporters"},{"url":"https://farmerconnect.apeda.gov.in/Buyer/BuyerDirectory?BusinessType=Importer&Commodities=All&Country=All&Culture=en","name":"APEDA FarmerConnect importers","listing_type":"buyer","adapter":"apeda_buyers"},{"url":"https://agriexchange.apeda.gov.in/AgriDirectory/SProvider/Index","name":"APEDA recognised packhouses","listing_type":"logistics","adapter":"apeda_packhouses"}]'
    # 0 means crawl every public directory page advertised by the publisher.
    # Operators can set a positive page cap for a shorter development refresh.
    APEDA_EXPORTER_MAX_PAGES: int = 0
    APEDA_BUYER_MAX_PAGES: int = 0
    APEDA_PACKHOUSE_MAX_PAGES: int = 0
    APEDA_DIRECTORY_PAGE_DELAY_SECONDS: float = 0.12
    MAHADBT_SCHEME_INDEX_URL: str = "https://mahadbt.maharashtra.gov.in/Farmer/SchemeData/SchemeData?str=E9DDFA703C38E51A23C0254248DAFF28"
    MAHADBT_MAX_SCHEMES: int = 30
    FARMS_NETWORK_STATUS_ENABLED: bool = True
    FARMS_CHC_LOOKBACK_DAYS: int = 365
    FARMS_CHC_MAX_RECORDS: int = 5000

settings = Settings()
