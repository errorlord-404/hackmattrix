SIH Harness — Project Memory / Handoff

1. Project Vision

The project is an agentic farming assistant designed around the complete lifecycle of a farmer.

The goal is not to build another agriculture chatbot.

The system should:

understand the current state of a farm → reason using agricultural, weather, economic and IoT data → recommend actions → explain those recommendations → execute permitted actions through tools.

---

2. Core Idea

The system follows the farmer through the entire crop lifecycle:

Previous Harvest
      ↓
Soil Analysis
      ↓
Next Crop Selection
      ↓
Seed / Fertilizer Selection
      ↓
Land Preparation
      ↓
Sowing
      ↓
Crop Monitoring
      ↓
Irrigation / Weather / Disease Management
      ↓
Harvest Planning
      ↓
Labour / Machinery / Logistics
      ↓
Mandi / MSP / Storage / Export Decision
      ↓
Sale
      ↓
Profit Calculation
      ↓
Next Season

---

3. Main Architecture

The project is designed as multiple independent microservices/tools controlled by one central AI harness.

                    SIH HARNESS
                         │
                    Main LLM
                         │
                   Tool Router
                         │
       ┌─────────────────┼──────────────────┐
       │                 │                  │
    Backend             ML                IoT
       │                 │                  │
 Weather APIs      Crop Prediction     Sensors
 Schemes           Price Prediction    Pumps
 Market Data       Disease Vision      Smart Plugs
 Farm Data         Yield Models        ESP32

The LLM should mostly orchestrate tools, rather than contain all business logic itself.

---

4. Codex CLI Harness

We have forked OpenAI Codex CLI.

The Rust implementation is inside:

codex-rs/

Codex tools are mainly located around:

codex-rs/core/src/tools/

Existing handlers are under:

codex-rs/core/src/tools/handlers/

Our custom farming tools should be kept inside:

codex-rs/core/src/tools/handlers/sage/

Example:

sage/
├── mod.rs
├── soil_moisture.rs
├── soil_health.rs
├── weather.rs
├── irrigation.rs
├── crop_recommendation.rs
├── market_price.rs
├── disease_detection.rs
└── ...

The folder may still be called "sage" internally even though the overall project/harness is currently referred to as SIH Harness.

---

5. Tool Development Philosophy

Individual teammates do not need to understand the complete Codex architecture.

They should build independent functionality with:

Clear Input
    ↓
Independent Function / API
    ↓
Clear Output

Example:

INPUT

{
  "sensor_id": "soil_01"
}

OUTPUT

{
  "moisture_percent": 24.5
}

The integration team then converts/wraps this functionality into Rust Codex tools.

Therefore:

Team Microservice
       ↓
REST / Internal API
       ↓
Rust Tool Handler
       ↓
Codex Tool Registry
       ↓
Main Agent

---

6. Team Categories

Development is divided broadly into:

Frontend

- Farmer dashboard
- Human-centered UI
- Mobile interface
- Ask Sage interface
- Farm map
- Crop timeline
- Soil-health screen
- Weather screen
- Market dashboard
- Government scheme screen
- Profit dashboard
- Alerts
- Voice interface
- Explainability UI

---

Backend

- APIs
- Farmer profile
- Farm state
- Farm Digital Twin
- Crop lifecycle
- Soil services
- Weather integration
- Market data
- Supplier discovery
- Machinery discovery
- Government schemes
- MSP
- Export information
- Storage
- Logistics
- Finance
- Alerts
- Database
- Authentication
- Microservice integration

---

IoT

- ESP32
- Soil moisture sensor
- Temperature sensor
- Humidity sensor
- Optional pH/EC/NPK sensors
- Water-level sensor
- Smart plugs
- Pumps
- Valves
- Sprinklers
- Device communication
- Automatic irrigation
- Emergency shutoff
- Manual override

---

Rust / Harness

- Codex fork
- Tool handlers
- Tool registry
- Tool execution
- Microservice wrappers
- System prompt
- Agent orchestration
- Farmer context injection
- Permissions
- Confirmation system
- Logging
- Tool retries
- Tool timeouts
- Safety layer
- Streaming results to frontend

---

Machine Learning / AI

- Crop recommendation
- Crop suitability
- Crop rotation
- Yield prediction
- Crop-price forecasting
- Profit/risk estimation
- Disease detection
- Pest detection
- Disease severity
- Harvest prediction
- Irrigation intelligence
- Fertilizer recommendation
- Market optimization
- Vision API/model integration

---

7. Farm Digital Twin

A major architectural concept is the Farm Digital Twin.

The system should continuously know:

Farmer
  │
  ├── Fields
  │
  ├── Previous Crops
  │
  ├── Current Crop
  │
  ├── Crop Stage
  │
  ├── Soil State
  │
  ├── Sensor State
  │
  ├── Irrigation History
  │
  ├── Fertilizer History
  │
  ├── Disease History
  │
  ├── Expenses
  │
  ├── Harvest History
  │
  └── Sales History

The LLM should make decisions based on this state rather than answering every query independently.

---

8. Database Architecture

We decided to use a dual/hierarchical database architecture.

Central Database - MongoDB

The server database contains information common to all farmers.

Examples:

- Crop information
- Crop requirements
- Crop rotation information
- Fertilizers
- Seeds
- Government schemes
- MSP information
- General mandi information
- Disease knowledge
- Agronomy information
- Common reference data

---

Personal SQLite Database

Each farmer/application instance has its own SQLite database containing only that farmer's application data.

Example:

farmer_A.sqlite

contains only Farmer A's data.

Another farmer has:

farmer_B.sqlite

The databases are independent.

Personal SQLite can contain:

- Farmer profile
- Fields
- Previous crops
- Current crop
- Crop cycles
- Soil readings
- Sensor readings
- Irrigation history
- Fertilizer history
- Disease history
- Expenses
- Harvests
- Sales
- Tasks
- Preferences

Because every SQLite DB belongs to one farmer, we do not need "farmer_id" on every personal table.

However, the SQLite DB should still have sensible internal tables such as:

fields
crop_cycles
soil_readings
sensor_readings
irrigation_events
expenses
harvests
sales

rather than storing everything in one giant table.

---

9. Crop Recommendation

Before each season the farmer provides information such as:

- Previous crop
- Soil information
- Water availability
- Preferences

The system automatically considers:

- Current location
- Season
- Weather
- Soil health
- Crop rotation
- Nutrient depletion
- Historical crop information
- Expected yield
- Expected crop price
- Input cost
- Expected profit
- Risk

The output should rank suitable crops and explain why.

Example:

1. Chickpea
Expected profit: ₹X
Water requirement: Low
Soil compatibility: Good
Crop rotation benefit: High

2. Wheat
Expected profit: ₹Y
Water requirement: Medium
...

---

10. Soil Health

Possible parameters:

- Moisture
- pH
- Nitrogen
- Phosphorus
- Potassium
- EC
- Temperature
- Organic carbon where available

Functions include:

get_soil_moisture()
get_soil_ph()
get_soil_npk()
get_soil_health()
analyse_soil()
detect_nutrient_deficiency()
recommend_fertilizer()

---

11. Weather Intelligence

Weather must be location specific.

Functions:

get_current_weather()
get_hourly_forecast()
get_daily_forecast()
get_rain_probability()
get_weather_alerts()

Weather should influence other decisions.

Example:

Soil moisture low
+
85% rain probability tomorrow

→ Do not irrigate immediately

rather than blindly turning the pump on.

---

12. Irrigation / IoT Automation

Basic architecture:

Sensor
   ↓
ESP32 / IoT Gateway
   ↓
Backend
   ↓
SIH Agent
   ↓
Decision
   ↓
Safety Check
   ↓
Smart Plug / Pump / Valve

Functions:

get_soil_moisture()
check_irrigation_requirement()
calculate_irrigation_duration()
start_irrigation()
stop_irrigation()
open_valve()
close_valve()

---

13. Safety Architecture

The LLM should not directly operate hardware.

Actions should have categories.

READ_ONLY
PHYSICAL_ACTION
FINANCIAL_ACTION
HIGH_RISK_ACTION

Example:

get_weather()
→ automatic

get_soil_moisture()
→ automatic

start_irrigation()
→ policy/confirmation

buy_fertilizer()
→ confirmation

apply_pesticide()
→ strict confirmation + validated guidance

This provides bounded autonomy rather than uncontrolled autonomy.

---

14. Computer Vision

Farmer uploads a picture of a crop.

System should provide:

- Possible disease
- Possible pest
- Confidence
- Severity
- Treatment recommendation
- Follow-up instructions

For MVP, use a strong existing vision model/API instead of training models for every possible crop disease.

Functions:

diagnose_crop_image()
detect_crop_disease()
detect_crop_pest()
estimate_disease_severity()
recommend_disease_treatment()

---

15. Seeds / Fertilizers / Inputs

System can recommend:

- Suitable seeds
- Suitable fertilizers
- Nearby dealers
- Prices
- Certifications
- Manufacturer claims/guarantees where verifiable

The system should distinguish verified facts from marketing claims.

Functions:

recommend_seed()
recommend_fertilizer_product()
find_seed_suppliers()
find_fertilizer_suppliers()
compare_farm_inputs()

---

16. Machinery

Farmer may need:

- Tractor
- Seeder
- Rotavator
- Sprayer
- Harvester
- Other equipment

Initially provide nearby rental/service discovery rather than building a complete marketplace.

Functions:

find_machinery()
find_tractor_rental()
find_harvester_rental()
find_custom_hiring_centres()
compare_machinery_costs()

---

17. Crop Lifecycle

Once a crop is selected, Sage should create its season timeline.

Example:

Sowing
 ↓
Germination
 ↓
Vegetative Stage
 ↓
Flowering
 ↓
Grain/Fruit Development
 ↓
Harvest

The system should give stage-specific:

- Irrigation guidance
- Fertilizer guidance
- Disease risks
- Weather risks
- Tasks
- Harvest prediction

Functions:

create_crop_lifecycle()
get_current_crop_stage()
update_crop_stage()
get_stage_recommendations()
predict_harvest_date()

---

18. Market Intelligence

The system should collect:

- Mandi prices
- Nearby market prices
- Historical prices
- Price trends
- Forecasts
- Market volatility

Functions:

get_market_price()
get_nearby_mandi_prices()
get_price_history()
predict_crop_price()
get_price_trend()

---

19. Economic Selling Decision

The system should not recommend the mandi with the highest price blindly.

Instead calculate:

Net Realisation =
Sale Revenue
- Transport
- Loading
- Unloading
- Market Fees
- Storage
- Expected Spoilage

Example:

Pune:
₹44,000 revenue
₹1,500 expenses
NET = ₹42,500

Mumbai:
₹48,000 revenue
₹7,200 expenses
NET = ₹40,800

Recommendation:
Sell in Pune

Functions:

compare_mandis()
calculate_transport_cost()
calculate_sale_cost()
calculate_net_realization()
recommend_best_market()

---

20. Storage

The farmer may need to decide:

Sell Now
vs
Store
vs
Sell Later

Functions:

find_storage_facilities()
find_warehouse()
find_cold_storage()
calculate_storage_cost()
estimate_storage_loss()
compare_sell_vs_store()

---

21. Logistics

Functions:

find_transport()
calculate_route()
calculate_logistics_cost()
estimate_transport_loss()
compare_logistics_options()

---

22. Government Schemes

System should find applicable schemes and explain:

- Eligibility
- Required documents
- Deadlines
- Benefits
- Application procedure
- Official source

Functions:

find_government_schemes()
check_scheme_eligibility()
get_scheme_details()
get_required_documents()
get_application_steps()

---

23. MSP / Distress Sale

If market prices collapse, Sage should check support options.

Functions:

get_msp()
compare_msp_with_market()
find_procurement_centres()
get_msp_sale_process()

---

24. Export Support

For suitable high-value crops the system can explain:

- Export requirements
- Quality requirements
- Certifications
- Organic farming requirements
- Exporters
- Logistics
- Expected costs

Functions:

check_export_eligibility()
get_export_requirements()
get_certification_requirements()
find_exporters()
estimate_export_cost()
compare_export_vs_domestic()

---

25. Farm Finance

Track the entire season financially.

Expenses:

- Seeds
- Fertilizer
- Pesticides
- Labour
- Machinery
- Irrigation
- Transport
- Storage

Functions:

record_expense()
record_income()
get_total_cost()
get_total_revenue()
calculate_profit()
calculate_profit_per_acre()
compare_season_profit()

---

26. Multilingual / Sarvam

The app should support local Indian languages using Sarvam or equivalent APIs.

Pipeline:

Farmer speaks Marathi/Hindi/etc.
        ↓
Speech-to-Text
        ↓
Translation to English
        ↓
Main LLM
        ↓
English response
        ↓
Translation to farmer language
        ↓
Text-to-Speech

Functions:

detect_language()
speech_to_text()
translate_to_english()
translate_from_english()
text_to_speech()

---

27. Human-Centered Explainability

Every major recommendation should answer:

WHAT should I do?
WHY should I do it?
WHEN should I do it?
HOW MUCH will it cost?
WHAT benefit should I expect?
WHAT alternatives exist?

Example:

Recommendation:
Irrigate tomorrow morning.

Why?
Soil moisture: 19%
Rain probability: 8%
Crop stage: Grain filling
Temperature: 32°C

Confidence:
High

---

28. Provenance / Trust

Important external data should include:

- Source
- Timestamp
- Location
- Freshness
- Confidence

The LLM should not invent:

- Weather
- MSP
- Mandi prices
- Government rules
- Fertilizer doses
- Sensor values

These should come from tools/data sources.

---

29. Offline Support

Because the target users may have unreliable connectivity:

- Personal data remains available in SQLite
- Crop timeline remains accessible
- Sensor data can still be read locally
- Farm events can be recorded
- Actions can be queued
- Data can synchronize when connectivity returns

---

30. Main MVP Features

The first complete version should focus on:

1. Farmer profile
2. Farm Digital Twin
3. Soil information
4. Weather
5. Crop recommendation
6. Crop lifecycle
7. Soil-moisture IoT
8. Smart irrigation
9. Disease image diagnosis
10. Market prices
11. Mandi/net-profit comparison
12. Basic machinery/supplier discovery
13. Government schemes/MSP
14. Farm profit calculation
15. Multilingual voice
16. Explainable recommendations
17. Codex tool orchestration

Do not attempt to fully productionize every proposed marketplace/export/storage feature during the hackathon.

---

31. Ideal Demo Story

The demo should be one continuous farmer journey.

Farmer asks:
"What should I grow next?"

        ↓

Sage checks:
Previous crop
Soil
Weather
Water
Prices
Costs
Crop rotation

        ↓

Sage recommends crop
and explains why.

        ↓

Farmer accepts.

        ↓

Crop lifecycle created.

        ↓

During cultivation:
Moisture becomes low.

        ↓

Sage checks weather.

        ↓

No rain expected.

        ↓

Sage recommends irrigation.

        ↓

Farmer approves.

        ↓

Smart plug/pump physically activates.

        ↓

Later:
Farmer uploads diseased crop image.

        ↓

Vision diagnoses disease.

        ↓

Near harvest:
Sage compares markets.

        ↓

Mandi prices
+
Transport
+
Storage
+
MSP

        ↓

Best economic option recommended.

        ↓

Sale recorded.

        ↓

Season profit calculated.

        ↓

This history becomes input for next season.

---

32. Project Positioning

The project should be presented as:

«An agentic farm operating system that maintains a digital twin of the farm, combines agronomy, weather, markets, IoT and government services, explains decisions in the farmer's own language, and can perform bounded real-world actions through tools.»

The differentiator is not the number of features.

The differentiator is that all these services operate together throughout the farmer's complete lifecycle under one intelligent harness.