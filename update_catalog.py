import os, json

def write(filepath, content):
    d = os.path.dirname(filepath)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Wrote: {filepath}")

# 1. Update Config with expanded categories
write('backend/app/config.py', '''import os
from pydantic import BaseModel
from typing import Optional, List

class Settings(BaseModel):
    PROJECT_NAME: str = "AeroPay - Agentic Commerce & Revenue Growth Engine"
    API_V1_STR: str = "/api/v1"
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    
    # Razorpay Test Credentials
    RAZORPAY_KEY_ID: str = os.getenv("RAZORPAY_KEY_ID", "rzp_test_aeropay_demo_key")
    RAZORPAY_KEY_SECRET: str = os.getenv("RAZORPAY_KEY_SECRET", "rzp_test_secret_aeropay_2026")
    RAZORPAY_WEBHOOK_SECRET: str = os.getenv("RAZORPAY_WEBHOOK_SECRET", "whsec_aeropay_webhook_secret_9988")
    
    # Cryptographic Audit Secret
    AUDIT_HMAC_SECRET: str = os.getenv("AUDIT_HMAC_SECRET", "aeropay_cryptographic_audit_signing_key_402")
    
    # Deterministic Guardrail Defaults
    DEFAULT_MAX_TXN_AMOUNT_INR: float = 60000.0   # Default transaction ceiling (supports smartphones & high-end workstations)
    DEFAULT_MAX_CUMULATIVE_SPEND_INR: float = 150000.0
    DEFAULT_APPROVAL_THRESHOLD_INR: float = 30000.0  # Orders > ₹30,000 require human-in-the-loop confirmation
    DEFAULT_MAX_ITEM_QUANTITY: int = 5
    ALLOWED_CURRENCY: str = "INR"
    ALLOWED_CATEGORIES: List[str] = [
        "smartphones",
        "mobile_accessories",
        "mechanical_keyboards",
        "computer_peripherals",
        "workspace_accessories",
        "developer_gear",
        "ergonomics",
        "audio_equipment"
    ]
    MERCHANT_ID: str = "merch_aeropay_electronics_01"
    MERCHANT_NAME: str = "AeroNation Tech & Lifestyle Store"

settings = Settings()
''')

# 2. Expanded Catalog with Compact Smartphones & Peripherals
catalog_data = [
    {
        "id": "sku_phone_zenfone_10_compact",
        "name": "Asus Zenfone 10 Compact Flagship (5.9\" 144Hz AMOLED)",
        "category": "smartphones",
        "price": 48499.0,
        "currency": "INR",
        "inventory": 18,
        "rating": 4.9,
        "review_count": 215,
        "shipping_eta_hours": 24,
        "tags": ["smartphone", "phone", "mobile", "small_display", "compact_phone", "small_screen", "5.9_inch", "snapdragon_8_gen_2", "one_hand"],
        "specs": {
            "display": "5.9-inch 144Hz HDR10+ Compact AMOLED (146.5 x 68.1 mm)",
            "processor": "Qualcomm Snapdragon 8 Gen 2 (4nm)",
            "ram_storage": "8GB LPDDR5X + 256GB UFS 4.0",
            "camera": "50MP Sony IMX766 with 6-Axis Hybrid Gimbal Stabilizer 2.0",
            "battery": "4300mAh with 30W HyperCharge + 15W Wireless Charging"
        },
        "complementary_product_ids": ["sku_acc_gan_charger_65w", "sku_acc_mag_case_glass"],
        "image_url": "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=600&auto=format&fit=crop&q=80",
        "description": "The ultimate pocket-sized flagship smartphone with a 5.9-inch compact display, flagship Snapdragon 8 Gen 2, and 6-axis gimbal stabilization."
    },
    {
        "id": "sku_phone_pixel_8a_compact",
        "name": "Google Pixel 8a 5G (6.1\" Actua OLED Compact Display)",
        "category": "smartphones",
        "price": 42999.0,
        "currency": "INR",
        "inventory": 24,
        "rating": 4.8,
        "review_count": 480,
        "shipping_eta_hours": 24,
        "tags": ["smartphone", "phone", "mobile", "small_display", "compact_phone", "google_pixel", "pixel_8a", "ai_phone", "6.1_inch", "oled"],
        "specs": {
            "display": "6.1-inch Actua OLED 120Hz (Up to 2000 nits peak)",
            "processor": "Google Tensor G3 with Titan M2 security coprocessor",
            "ram_storage": "8GB RAM + 128GB Storage",
            "camera": "64MP Quad PD wide + 13MP ultrawide with Best Take & Magic Editor",
            "battery": "4492mAh with 24-hour battery life and Fast Charging"
        },
        "complementary_product_ids": ["sku_acc_gan_charger_65w", "sku_audio_anc_headset"],
        "image_url": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=600&auto=format&fit=crop&q=80",
        "description": "Compact 6.1-inch Google AI-powered phone with incredible camera performance and 7 years of OS updates."
    },
    {
        "id": "sku_phone_galaxy_s23_compact",
        "name": "Samsung Galaxy S23 5G (6.1\" Dynamic AMOLED 2X)",
        "category": "smartphones",
        "price": 49999.0,
        "currency": "INR",
        "inventory": 15,
        "rating": 4.85,
        "review_count": 620,
        "shipping_eta_hours": 24,
        "tags": ["smartphone", "phone", "mobile", "small_display", "compact", "samsung", "galaxy_s23", "small_screen", "6.1_inch", "flagship"],
        "specs": {
            "display": "6.1-inch Flat FHD+ Dynamic AMOLED 2X (120Hz Adaptive)",
            "processor": "Snapdragon 8 Gen 2 for Galaxy",
            "ram_storage": "8GB RAM + 128GB Storage",
            "camera": "50MP Wide + 12MP Ultra-Wide + 10MP 3x Optical Telephoto",
            "body": "Armor Aluminum frame with Gorilla Glass Victus 2 (IP68)"
        },
        "complementary_product_ids": ["sku_acc_gan_charger_65w", "sku_acc_mag_case_glass"],
        "image_url": "https://images.unsplash.com/photo-1610945265064-0e34e5519bbf?w=600&auto=format&fit=crop&q=80",
        "description": "Ultra-sleek 6.1-inch compact flagship with Snapdragon 8 Gen 2 and pro-grade triple cameras."
    },
    {
        "id": "sku_phone_iphone_13_mini",
        "name": "Apple iPhone 13 mini (5.4\" Super Retina XDR)",
        "category": "smartphones",
        "price": 46999.0,
        "currency": "INR",
        "inventory": 10,
        "rating": 4.9,
        "review_count": 890,
        "shipping_eta_hours": 24,
        "tags": ["phone", "smartphone", "iphone", "apple", "small_display", "compact", "mini_phone", "5.4_inch", "ios"],
        "specs": {
            "display": "5.4-inch Super Retina XDR OLED (Compact one-hand design)",
            "processor": "A15 Bionic chip (6-core CPU + 4-core GPU)",
            "ram_storage": "128GB Storage",
            "camera": "Advanced dual 12MP system with Sensor-shift OIS & Cinematic mode",
            "build": "Ceramic Shield front + Aerospace-grade aluminum"
        },
        "complementary_product_ids": ["sku_acc_gan_charger_65w", "sku_acc_mag_case_glass"],
        "image_url": "https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=600&auto=format&fit=crop&q=80",
        "description": "The most powerful compact 5.4-inch smartphone ever made with A15 Bionic and Cinematic 4K video."
    },
    {
        "id": "sku_acc_gan_charger_65w",
        "name": "AeroFast 65W GaN Dual USB-C Ultra-Compact Fast Charger",
        "category": "mobile_accessories",
        "price": 1499.0,
        "currency": "INR",
        "inventory": 85,
        "rating": 4.85,
        "review_count": 340,
        "shipping_eta_hours": 12,
        "tags": ["charger", "gan_charger", "65w", "fast_charging", "usb_c", "phone_accessory"],
        "specs": {"power": "65W GaN III Technology", "ports": "2x USB-C PD 3.0 + 1x USB-A QC 4.0", "safety": "Temperature Control & Over-voltage Protection"},
        "complementary_product_ids": ["sku_phone_zenfone_10_compact", "sku_phone_pixel_8a_compact"],
        "image_url": "https://images.unsplash.com/photo-1583863788434-e58a36330cf0?w=600&auto=format&fit=crop&q=80",
        "description": "Pocket-sized 65W Gallium Nitride fast charger capable of charging phones, tablets, and laptops simultaneously."
    },
    {
        "id": "sku_acc_mag_case_glass",
        "name": "AeroGuard Magnetic Armor Case + 9H Tempered Glass Screen Protector",
        "category": "mobile_accessories",
        "price": 799.0,
        "currency": "INR",
        "inventory": 110,
        "rating": 4.75,
        "review_count": 290,
        "shipping_eta_hours": 12,
        "tags": ["phone_case", "screen_protector", "tempered_glass", "magsafe", "drop_protection"],
        "specs": {"material": "Shock-absorbing TPU + Matte Polycarbonate", "magnets": "N52 Strong Magnetic Ring", "glass": "9H Hardness Edge-to-Edge"},
        "complementary_product_ids": ["sku_phone_pixel_8a_compact", "sku_phone_galaxy_s23_compact"],
        "image_url": "https://images.unsplash.com/photo-1601784551446-20c9e07cdbdb?w=600&auto=format&fit=crop&q=80",
        "description": "Military-grade drop protection case with embedded magnetic charging ring and oleophobic 9H tempered glass."
    },
    {
        "id": "sku_kb_keychron_k2",
        "name": "Keychron K2 V2 Wireless Mechanical Keyboard",
        "category": "mechanical_keyboards",
        "price": 4499.0,
        "currency": "INR",
        "inventory": 28,
        "rating": 4.8,
        "review_count": 342,
        "shipping_eta_hours": 24,
        "tags": ["mechanical_keyboard", "wireless", "bluetooth", "hot_swappable", "mac_windows", "rgb", "brown_switch"],
        "specs": {"switches": "Gateron G Pro Brown", "layout": "75% compact (84 keys)", "battery": "4000mAh", "connectivity": "Bluetooth 5.1 & Type-C"},
        "complementary_product_ids": ["sku_acc_wrist_rest_walnut", "sku_acc_custom_coiled_cable"],
        "image_url": "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=600&auto=format&fit=crop&q=80",
        "description": "75% layout compact wireless mechanical keyboard designed for maximum productivity and premium tactile typing."
    },
    {
        "id": "sku_kb_royal_kludge_rk84",
        "name": "Royal Kludge RK84 Tri-Mode RGB Mechanical Keyboard",
        "category": "mechanical_keyboards",
        "price": 3999.0,
        "currency": "INR",
        "inventory": 45,
        "rating": 4.6,
        "review_count": 512,
        "shipping_eta_hours": 24,
        "tags": ["mechanical_keyboard", "tri_mode", "rgb", "hot_swappable", "red_switch", "budget_friendly"],
        "specs": {"switches": "RK Red Linear Switches", "layout": "84 Keys", "connectivity": "2.4Ghz, BT 5.0, USB-C", "battery": "3750mAh"},
        "complementary_product_ids": ["sku_acc_wrist_rest_walnut", "sku_acc_custom_coiled_cable"],
        "image_url": "https://images.unsplash.com/photo-1618384887929-16ec33fab9ef?w=600&auto=format&fit=crop&q=80",
        "description": "Ultra-versatile 84-key mechanical keyboard with tri-mode connectivity and smooth linear switches."
    },
    {
        "id": "sku_kb_ducky_one3_tkl",
        "name": "Ducky One 3 TKL Pure White Mechanical Keyboard",
        "category": "mechanical_keyboards",
        "price": 4899.0,
        "currency": "INR",
        "inventory": 14,
        "rating": 4.9,
        "review_count": 189,
        "shipping_eta_hours": 48,
        "tags": ["mechanical_keyboard", "tkl", "cherry_mx", "pbt_keycaps", "audiophile_acoustics"],
        "specs": {"switches": "Cherry MX Blue / Brown", "layout": "Tenkeyless (80%)", "keycaps": "Double-Shot PBT", "foam": "Silicone sound dampening"},
        "complementary_product_ids": ["sku_acc_wrist_rest_walnut", "sku_acc_deskmat_leather"],
        "image_url": "https://images.unsplash.com/photo-1595225476474-87563907a212?w=600&auto=format&fit=crop&q=80",
        "description": "Enthusiast grade mechanical keyboard with sound-dampening silicone layer and Cherry MX switches."
    },
    {
        "id": "sku_kb_custom_pro_aluminium",
        "name": "AeroPro CNC Anodized Aluminium Gasket Keyboard",
        "category": "mechanical_keyboards",
        "price": 7999.0,
        "currency": "INR",
        "inventory": 8,
        "rating": 4.95,
        "review_count": 87,
        "shipping_eta_hours": 24,
        "tags": ["mechanical_keyboard", "premium", "gasket_mount", "aluminium_body", "high_end"],
        "specs": {"body": "CNC 6063 Aluminum", "weight": "1.8kg", "mount": "Gasket with Poron Foam", "switches": "Gateron Oil King"},
        "complementary_product_ids": ["sku_acc_custom_coiled_cable", "sku_acc_deskmat_leather"],
        "image_url": "https://images.unsplash.com/photo-1541140532154-b024d705b909?w=600&auto=format&fit=crop&q=80",
        "description": "Flagship full CNC-machined aluminium gasket mounted keyboard for connoisseurs."
    },
    {
        "id": "sku_acc_wrist_rest_walnut",
        "name": "Ergonomic Solid Walnut Wood Keyboard Wrist Rest",
        "category": "workspace_accessories",
        "price": 499.0,
        "currency": "INR",
        "inventory": 120,
        "rating": 4.85,
        "review_count": 430,
        "shipping_eta_hours": 12,
        "tags": ["wrist_rest", "ergonomics", "walnut_wood", "keyboard_accessory", "anti_slip"],
        "specs": {"material": "Natural Solid Walnut Wood", "size": "317mm x 80mm x 19mm", "finish": "Natural Organic Wax Oil"},
        "complementary_product_ids": ["sku_kb_keychron_k2", "sku_kb_royal_kludge_rk84"],
        "image_url": "https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=600&auto=format&fit=crop&q=80",
        "description": "Handcrafted solid walnut wrist rest designed to maintain neutral wrist posture during long sessions."
    },
    {
        "id": "sku_acc_custom_coiled_cable",
        "name": "Aviator Coiled USB-C Braided Keyboard Cable",
        "category": "computer_peripherals",
        "price": 799.0,
        "currency": "INR",
        "inventory": 60,
        "rating": 4.7,
        "review_count": 210,
        "shipping_eta_hours": 24,
        "tags": ["cable", "aviator_connector", "coiled_cable", "usb_c", "custom_keyboard"],
        "specs": {"connector": "GX12 4-Pin Aviator", "sleeve": "Double-sleeved Paracord + Techflex", "length": "1.5m + 15cm coil"},
        "complementary_product_ids": ["sku_kb_keychron_k2", "sku_kb_royal_kludge_rk84"],
        "image_url": "https://images.unsplash.com/photo-1544652478-6653e09f18a2?w=600&auto=format&fit=crop&q=80",
        "description": "Custom mechanical keyboard cable with metallic aviator detachable connector."
    },
    {
        "id": "sku_acc_deskmat_leather",
        "name": "AeroNation Premium Vegan Leather Desk Mat (90x40cm)",
        "category": "workspace_accessories",
        "price": 699.0,
        "currency": "INR",
        "inventory": 90,
        "rating": 4.75,
        "review_count": 380,
        "shipping_eta_hours": 24,
        "tags": ["deskmat", "mousepad", "waterproof", "vegan_leather", "desk_pad"],
        "specs": {"dimensions": "900 x 400 x 2mm", "material": "Dual-sided PU Leather", "features": "Waterproof, easy wipe clean"},
        "complementary_product_ids": ["sku_kb_keychron_k2", "sku_mouse_ergo_vertical"],
        "image_url": "https://images.unsplash.com/photo-1629429408209-1f912961dbd8?w=600&auto=format&fit=crop&q=80",
        "description": "Spacious water-resistant desk protector mat for keyboard and mouse precision."
    },
    {
        "id": "sku_mouse_ergo_vertical",
        "name": "AeroGrip Ergonomic Wireless Vertical Mouse",
        "category": "ergonomics",
        "price": 1899.0,
        "currency": "INR",
        "inventory": 55,
        "rating": 4.7,
        "review_count": 295,
        "shipping_eta_hours": 24,
        "tags": ["mouse", "ergonomic", "vertical_mouse", "wireless", "rsi_prevention"],
        "specs": {"angle": "57 degrees natural handshake angle", "dpi": "800-1600-2400 DPI", "sensor": "Optical Precision", "battery": "Rechargeable Type-C"},
        "complementary_product_ids": ["sku_acc_deskmat_leather", "sku_acc_wrist_rest_walnut"],
        "image_url": "https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?w=600&auto=format&fit=crop&q=80",
        "description": "Ergonomically sculpted vertical mouse designed to prevent carpal tunnel strain and arm fatigue."
    },
    {
        "id": "sku_audio_anc_headset",
        "name": "AeroSound Pro Hybrid ANC Wireless Headphones",
        "category": "audio_equipment",
        "price": 3499.0,
        "currency": "INR",
        "inventory": 32,
        "rating": 4.8,
        "review_count": 220,
        "shipping_eta_hours": 24,
        "tags": ["audio", "anc", "noise_cancelling", "bluetooth_5_3", "spatial_audio", "hi_res"],
        "specs": {"drivers": "40mm Titanium Dynamic", "anc_depth": "38dB Hybrid Active Noise Cancellation", "battery_life": "50 Hours Playtime"},
        "complementary_product_ids": ["sku_acc_headphone_stand_wood"],
        "image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&auto=format&fit=crop&q=80",
        "description": "Immersive studio headphones with high-res active noise cancellation for deep work focus."
    },
    {
        "id": "sku_acc_headphone_stand_wood",
        "name": "Minimalist Solid Oak Headphone Stand",
        "category": "workspace_accessories",
        "price": 599.0,
        "currency": "INR",
        "inventory": 40,
        "rating": 4.6,
        "review_count": 110,
        "shipping_eta_hours": 24,
        "tags": ["headphone_stand", "desk_accessory", "wood", "minimalist"],
        "specs": {"material": "Solid Oak + Matte Aluminium Pillar", "base": "Weighted anti-slip silicon base"},
        "complementary_product_ids": ["sku_audio_anc_headset"],
        "image_url": "https://images.unsplash.com/photo-1584679109597-c656b19974c9?w=600&auto=format&fit=crop&q=80",
        "description": "Architectural headphone display stand keeping desk clear and organized."
    },
    {
        "id": "sku_dev_screenbar_light",
        "name": "AeroBeam Pro Monitor ScreenBar LED Light Bar",
        "category": "developer_gear",
        "price": 2299.0,
        "currency": "INR",
        "inventory": 38,
        "rating": 4.85,
        "review_count": 310,
        "shipping_eta_hours": 24,
        "tags": ["screenbar", "desk_light", "eye_care", "anti_glare", "touch_control"],
        "specs": {"lighting": "Asymmetric Optical Design (Zero Screen Glare)", "color_temp": "2800K - 6500K Adjustable", "power": "USB 5V/1A"},
        "complementary_product_ids": ["sku_acc_deskmat_leather", "sku_kb_keychron_k2"],
        "image_url": "https://images.unsplash.com/photo-1593642632823-8f785ba67e45?w=600&auto=format&fit=crop&q=80",
        "description": "Asymmetric glare-free monitor light bar engineered to protect eyes during late-night coding sessions."
    },
    {
        "id": "sku_dev_usbc_dock_11in1",
        "name": "AeroConnect 11-in-1 Dual 4K USB-C Hub & Dock",
        "category": "developer_gear",
        "price": 2999.0,
        "currency": "INR",
        "inventory": 25,
        "rating": 4.7,
        "review_count": 190,
        "shipping_eta_hours": 24,
        "tags": ["usb_hub", "docking_station", "dual_4k_hdmi", "100w_power_delivery", "gigabit_ethernet"],
        "specs": {"ports": "2x HDMI 4K@60Hz, 1x 100W PD USB-C, 3x USB 3.0, 1x Gigabit RJ45, SD/TF, Audio Jack", "chassis": "Aerospace Grade Aluminum"},
        "complementary_product_ids": ["sku_dev_screenbar_light", "sku_kb_keychron_k2"],
        "image_url": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=600&auto=format&fit=crop&q=80",
        "description": "High speed 100W Power Delivery 11-in-1 multi-port docking station for multi-monitor developer setups."
    }
]

write('backend/app/data/catalog_db.json', json.dumps(catalog_data, indent=2))
print("Catalog updated with compact phones!")
