"""Multi-scenario pipeline: diverse editorial angles from DB data.

7 scenarios with ZERO image/solution overlap:
1. Jennie x Chloé — 소프트 럭셔리의 정석
2. Lisa x STELLA McCARTNEY — 지속가능한 하이패션
3. Rosé x SAINT LAURENT — 올드머니 뉴웨이브
4. Jisoo x Cartier — 주얼리가 완성하는 스타일
5. Danielle x 스트릿 브랜드 — 뉴진스 막내 라인의 캐주얼 감성
6. Jennie vs Lisa — BLACKPINK 투톱 스타일 배틀
7. K-POP 공항패션 크로스오버 — 4세대 아이콘 총집합
"""

import asyncio
import logging
import time
import uuid

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)

R2 = "https://pub-6354054b117b46b9a0fe99e4a546e681.r2.dev"

# Solution product URLs from DB — injected into enriched_contexts for link_url enrichment
SOLUTION_URLS: dict[str, str] = {
    "Chloé Ribbed Knit Wool Tank Top": "https://www.chloe.com/en-rs/p/ready-to-wear/top/CH25UMH1476770L.html",
    "STANLEY The Quencher® Luxe Tumbler": "https://www.stanley1913.com/products/cyber-monday-quencher-luxe-h2-0-flowstate-tumbler-40-oz",
    "STANLEY All Day Slim Bottle": "https://www.stanley1913.com/products/the-all-day-slim-bottle-20-oz",
    "adidas Adicolor Essentials Crew Sweatshirt": "https://www.adidas.com/us/adicolor-essentials-crew-sweatshirt/IR5971.html",
    "Rolling Stone Modern Logo Dad Hat": "https://shop.rollingstone.com/products/rolling-stone-modern-logo-dad-hat-black",
    "MOSKI EYEWEAR Amsterdam Sunglasses": "https://www.instagram.com/moskiparis/",
    "beats by dr.dre Beats Studio Pro Wireless Headphones": "https://www.bhphotovideo.com/c/product/1774620-REG/",
    "PORTER TOKYO JAPAN Explorer Daypack": "https://www.yoshidakaban.com/en/product/105946.html",
    "STELLA McCARTNEY Popper-Studded Bootcut Denim Jeans": "https://www.stellamccartney.com/us/en/popper-studded-bootcut-denim-jeans-6D03373SQH00423328.html",
    "BVLGARI B.Zero1 Ring": "https://www.bulgari.com/en-us/jewelry/rings/b-zero1-ring-white-gold-323530",
    "BVLGARI B.Zero1 Bracelet": "https://www.bulgari.com/en-us/jewelry/bracelets/b-zero1-bracelet-rose-gold-ceramic-black-351415",
    "GALLERY DEPT. Ebay Tee": "https://gallerydept.com/products/ebay-tee",
    "Acne Studios Studded Jeans - Loose Fit": "https://www.acnestudios.com/us/en/man/jeans/",
    "LOUIS VUITTON LV Malletage Round Sunglasses": "https://us.louisvuitton.com/eng-us/products/lv-malletage-light-round-sunglasses-s00-nvprod4670047v/Z2044W",
    "Coperni Stripped Cropped Shirt": "https://thewebster.com/shopv/coperni-tops",
    "Chrome Hearts Leather Cross Patch Blue Mini Bowling Bag": "https://shengliroadmarket.com/products/chrome-hearts-leather-cross-patch-blue-mini-bowling-bag",
    "BVLGARI Serpenti Viper Ring": "https://www.bulgari.com/en-us/AN858111.html",
    "SAINT LAURENT Cashmere Sweater": "https://www.ysl.com/en-us/ca/shop-women/ready-to-wear/knitwear",
    "THE ROW Domino Bag": "https://www.fashionphile.com/products/the-row-domino-bag-dark-chocolate-1513322",
    "New Era NY Yankees Dark Navy": "https://www.dickssportinggoods.com/p/new-era-mens-new-york-yankees-59fifty-game-navy-authentic-hat-17newmmlbynksnvygapa",
    "THE ROW Carlton Jeans": "https://www.amarees.com/products/carlton-jeans",
    "SAINT LAURENT SL M94": "https://www.fashioneyewear.com/en-us/products/saint-laurent-sl-m94",
    "TIFFANY & Co. Elsa Peretti Bone Ring": "https://www.tiffany.com/jewelry/rings/elsa-peretti-bone-ring-GRP12659/",
    "Brandy Melville Christy Hoodie": "https://us.brandymelville.com/products/christy-hoodie",
    "R13 Multi-Pocket Utility Pant": "https://www.r13.com/products/multi-pocket-utility-pant",
    "SAINT LAURENT SL M94 Sunglasses": "https://www.fashioneyewear.com/en-us/products/saint-laurent-sl-m94",
    "SAINT LAURENT Oversized Jacket in Lambskin": "https://modesens.com/product/saint-laurent-oversize-lambskin-leather-bomber-jacket/",
    "BLACKPINK World Tour Dad Cap": "https://www.kpopalbums.com/products/blackpink-deadline-world-tour-md",
    "Cartier Trinity Necklace": "https://www.cartier.com/en-us/jewelry/necklaces/trinity/",
    "Cartier Trinity Ring": "https://www.cartier.com/en-us/jewelry/rings/trinity/trinity-ring-classic-model-CRB4234200.html",
    "alo Cropped Cozy Day Full Zip Jacket": "https://www.aloyoga.com/products/w4568r-cropped-cozy-day-full-zip-jacket-ivory",
    "alo High-Waist Cozy Day Wide Pant": "https://www.aloyoga.com/products/w5041r-high-waist-cozy-day-wide-leg-pant",
    "LEMAIRE Large Croissant Bag (Soft Nappa Leather)": "https://www.lemaire.fr/products/large-croissant-bag-black-fall-winter",
    "alo Routine Cropped Zip Hoodie": "https://www.aloyoga.com/products/w3699r-routine-cropped-zip-hoodie-black",
    "alo High-Waist Night Out Cargo Trouser": "https://www.aloyoga.com/products/w5934r-high-waist-night-out-cargo-trouser",
    "DIOR Miss Dior Flap Bag": "https://www.dior.com/en_us/fashion/products/M2610UWIS_M900",
    "Cartier Tank Louis Watch": "https://www.chrono24.com/cartier/tank-louis-cartier--mod184.htm",
    "Chrome Hearts Triple Cross Beanie": "https://groupie.store/products/cross-patch-beanie-3",
    "NIKE Dugout Loose Satin Jacket": "https://www.kickscrew.com/products/nike-dugout-loose-satin-jacket-black-fq7970-010",
    "DEW E DEW E Flower Cap_Beige": "https://www.dew.world/store-1/p/s0ghxj4l7gtzf8xwquugxq0iuyd6q3",
    "Asamimichan Face Stuffed Mascot": "https://www.instagram.com/asamimichan/",
    "NIKE Air Max 90 LV8": "https://www.footlocker.com/product/model/nike-air-max-90-lv8/425010.html",
    "CELINE Slides": "https://www.celine.com/en-us/celine-shop-women/shoes/loafers-and-flats/",
    "CELINE Loose Celine Paris T-Shirt": "https://www.celine.com/en-us/celine-shop-women/ready-to-wear/t-shirts-and-sweatshirts/",
    "LANG & LU Loves Bunny T-Shirts": "https://langnlu.com/shop_view/?idx=860",
    "Wiggle Wiggle Smile We Love Cushion Blanket": "https://en.wiggle-wiggle.com/product/cushion-blanket-smile-we-love/",
    "BAPE x Alpha Industries Shark Full Zip Hoodie": "https://www.alphaindustries.com/products/csb53501c1-alpha-x-bape-shark-full-zip-hoodie",
    "Pintuck Cargo Denim Pants": "https://freakins.com/products/pintuck-denim-cargo-joggers",
    "NewJeans Club Cap": "https://weverseshop.io/",
    "FOUNDRÆ Pave Diamond Initial - Heart Beat Super Fine": "https://foundrae.com/products/super-fine-clip-18-pave-initial-heart-beat",
    "FOUNDRÆ Protection - Thin Champleve Enamel Band": "https://foundrae.com/collections/rings",
    "Supreme Waxed Wool 6-Panel": "https://www.supremecommunity.com/season/itemdetails/9238/",
    "young n sang Snowflake Vest": "https://youngnsang.com/product/snowflake-vest/129",
    "FOUNDRÆ Belcher Chain Necklace - Reverie": "https://www.twistonline.com/products/true-love-and-reverie-mixed-belcher-necklace",
    "Christian Louboutin Cassia Lace Up": "https://us.christianlouboutin.com/us_en/cassia-lace-up-black-lin-black-1250498b439.html",
    "ROJANATORN Baifern Necklace": "https://www.instagram.com/rojanatorn_official/",
    "LLOUD Light Pink Crop Tee": "https://thaishop.lalisaofficial.com/products/lloud-light-pink-tee",
    "LLOUD Light Pink Shorts": "https://thaishop.lalisaofficial.com/products/lloud-light-pink-shorts",
    "DEADLINE Embroidered Logo Ballcap": "https://www.kpopalbums.com/products/blackpink-deadline-world-tour-md-embroidered-logo-ballcap",
    "DSQUARED2 Mohair Mini Cape Knit": "https://www.dsquared2.com/ca/mohair-mini-cape-knit/S72HA1158S18357961S.html",
    "CHANEL Long Necklace": "https://www.chanel.com/us/fashion/p/ABF948B21130U2324/long-necklace/",
    "CHANEL Necklace": "https://www.chanel.com/us/fashion/costume-jewelry/c/1x1x3x3/necklaces/",
    "LOEWE Long Sleeve T-shirt": "https://www.loewe.com/usa/en/men/menswear/t-shirts-and-polos",
    "LOUIS VUITTON LV Day Cap": "https://eu.louisvuitton.com/eng-e1/products/lv-day-cap-s00-nvprod3720020v/M77806",
    "POP MART CRYBABY x Powerpuff Girls Series": "https://www.popmart.com/products/crybaby-x-powerpuff-girls-series",
    "R13 Shredded Seam Drop Neck Shirt - Leopard": "https://finefolk.com/products/r13-shredded-seam-drop-neck-shirt-leopard-ps25",
    "courrèges Baggy Wide-leg Twill Pants": "https://www.courreges.com/us/category/shop/ready-to-wear/trousers",
    "DIOR Medium Grand Tour Multipocket Bag": "https://www.dior.com/en_vn/fashion/products/M2433UNQD_M900",
    "DEADLINE WORLD TOUR Embroidered Logo Ballcap": "https://www.kpopalbums.com/products/blackpink-deadline-world-tour-md-embroidered-logo-ballcap",
}


def _inject_urls(scenarios: list[tuple[str, dict]]) -> None:
    """Inject original_url from SOLUTION_URLS lookup into all solution dicts."""
    for _, scenario in scenarios:
        for ctx in scenario.get("enriched_contexts", []):
            for sol in ctx.get("solutions", []):
                title = sol.get("title", "")
                if title in SOLUTION_URLS and "original_url" not in sol:
                    sol["original_url"] = SOLUTION_URLS[title]

# ──────────────────────────────────────────────
# Scenario 1: Jennie x Chloé — Soft Luxury
# ──────────────────────────────────────────────
SCENARIO_1 = {
    "seed_keyword": "제니 Chloé 소프트 럭셔리",
    "category": "fashion",
    "curated_topics": [
        {
            "keyword": "제니 Chloé 소프트 럭셔리",
            "trend_background": (
                "BLACKPINK 제니는 Chloé의 글로벌 앰배서더로서 '소프트 럭셔리' 트렌드의 "
                "중심에 서 있다. 리브드 니트 탱크탑, 캐시미어 아이템, 뉴트럴 톤 팔레트로 "
                "구성된 그녀의 스타일은 '과시하지 않는 럭셔리'의 정수를 보여준다. "
                "STANLEY 텀블러와 beats 헤드폰 같은 라이프스타일 아이템까지 "
                "자연스럽게 코디에 녹여내는 센스가 돋보인다."
            ),
            "related_keywords": ["soft luxury", "quiet luxury", "Chloé ambassador", "neutral palette", "effortless chic"],
        },
    ],
    "enriched_contexts": [
        {
            "artist_name": "jennie",
            "group_name": "BLACKPINK",
            "image_url": f"{R2}/blackpinkk.style/2025-09-14_21-28-37/2025-09-14_21-28-37_UTC_4.jpg",
            "solutions": [
                {"title": "Chloé Ribbed Knit Wool Tank Top", "thumbnail_url": f"{R2}/items/a0fdc6d4-70c2-4d8f-b45/thumb.jpg", "metadata": {"brand": "Chloé", "category": "Tops"}, "description": "Soft wool ribbed tank — the epitome of quiet luxury"},
                {"title": "STANLEY The Quencher® Luxe Tumbler", "thumbnail_url": f"{R2}/items/a0fdc6d4-70c2-4d8f-b45/thumb2.jpg", "metadata": {"brand": "STANLEY", "category": "Lifestyle"}, "description": "Gold tumbler — lifestyle flex meets fashion"},
                {"title": "STANLEY All Day Slim Bottle", "thumbnail_url": f"{R2}/items/d2cd78d7-5829-48ff-920/thumb.jpg", "metadata": {"brand": "STANLEY", "category": "Lifestyle"}, "description": "Slim water bottle — athleisure essential"},
            ],
        },
        {
            "artist_name": "jennie",
            "group_name": "BLACKPINK",
            "image_url": f"{R2}/blackpinkk.style/2024-07-22_09-01-42/2024-07-22_09-01-42_UTC_6.jpg",
            "solutions": [
                {"title": "adidas Adicolor Essentials Crew Sweatshirt", "thumbnail_url": f"{R2}/items/7d98863b-26b0-40c8-a02/thumb.jpg", "metadata": {"brand": "adidas", "category": "Tops"}, "description": "Classic crew neck — sporty chic base layer"},
                {"title": "Rolling Stone Modern Logo Dad Hat", "thumbnail_url": f"{R2}/items/7d98863b-26b0-40c8-a02/thumb2.jpg", "metadata": {"brand": "Rolling Stone", "category": "Accessories"}, "description": "Vintage band merch cap — cultural reference accent"},
                {"title": "MOSKI EYEWEAR Amsterdam Sunglasses", "thumbnail_url": f"{R2}/items/7d98863b-26b0-40c8-a02/thumb3.jpg", "metadata": {"brand": "MOSKI", "category": "Eyewear"}, "description": "Indie eyewear brand — understated oval frames"},
                {"title": "beats by dr.dre Beats Studio Pro Wireless Headphones", "thumbnail_url": f"{R2}/items/7d98863b-26b0-40c8-a02/thumb4.jpg", "metadata": {"brand": "beats", "category": "Tech"}, "description": "Premium headphones as fashion accessory"},
                {"title": "PORTER TOKYO JAPAN Explorer Daypack", "thumbnail_url": f"{R2}/items/7d98863b-26b0-40c8-a02/thumb5.jpg", "metadata": {"brand": "PORTER", "category": "Bags"}, "description": "Japanese craftsmanship meets minimal design"},
            ],
        },
    ],
}

# ──────────────────────────────────────────────
# Scenario 2: Lisa x STELLA McCARTNEY — Sustainable High Fashion
# ──────────────────────────────────────────────
SCENARIO_2 = {
    "seed_keyword": "리사 STELLA McCARTNEY 지속가능 패션",
    "category": "fashion",
    "curated_topics": [
        {
            "keyword": "리사 STELLA McCARTNEY 지속가능 패션",
            "trend_background": (
                "BLACKPINK 리사는 STELLA McCARTNEY와 BVLGARI를 중심으로 "
                "지속가능한 하이패션의 아이콘으로 자리매김했다. "
                "비건 레더, 재활용 소재 데님, 에코 프렌들리 주얼리를 자연스럽게 착용하며 "
                "패션과 환경의식의 조화를 보여준다. Gallery Dept.와 Acne Studios 같은 "
                "아트 지향 브랜드와의 믹스매치도 돋보인다."
            ),
            "related_keywords": ["sustainable fashion", "vegan leather", "BVLGARI", "eco luxury", "Gallery Dept"],
        },
    ],
    "enriched_contexts": [
        {
            "artist_name": "lisa",
            "group_name": "BLACKPINK",
            "image_url": f"{R2}/blackpinkk.style/2024-08-15_23-52-40/2024-08-15_23-52-40_UTC_6.jpg",
            "solutions": [
                {"title": "STELLA McCARTNEY Popper-Studded Bootcut Denim Jeans", "thumbnail_url": f"{R2}/items/aab03351-9617-4325-9f2/thumb.jpg", "metadata": {"brand": "STELLA McCARTNEY", "category": "Bottoms"}, "description": "Organic cotton bootcut denim with studded detail"},
                {"title": "BVLGARI B.Zero1 Ring", "thumbnail_url": f"{R2}/items/1db6d049-0d9a-4ad1-baa/thumb.jpg", "metadata": {"brand": "BVLGARI", "category": "Jewelry"}, "description": "Iconic spiral ring — timeless Italian craftsmanship"},
                {"title": "BVLGARI B.Zero1 Bracelet", "thumbnail_url": f"{R2}/items/aab03351-9617-4325-9f2/thumb2.jpg", "metadata": {"brand": "BVLGARI", "category": "Jewelry"}, "description": "Matching bracelet — jewelry layering done right"},
            ],
        },
        {
            "artist_name": "lisa",
            "group_name": "BLACKPINK",
            "image_url": f"{R2}/blackpinkk.style/2024-06-08_06-27-23/2024-06-08_06-27-23_UTC_4.jpg",
            "solutions": [
                {"title": "GALLERY DEPT. Ebay Tee", "thumbnail_url": f"{R2}/items/ca918bb1-3561-4e7f-92e/thumb.jpg", "metadata": {"brand": "GALLERY DEPT.", "category": "Tops"}, "description": "Art-meets-street vintage graphic tee"},
                {"title": "Acne Studios Studded Jeans - Loose Fit", "thumbnail_url": f"{R2}/items/ca918bb1-3561-4e7f-92e/thumb2.jpg", "metadata": {"brand": "Acne Studios", "category": "Bottoms"}, "description": "Scandinavian minimalism with punk edge"},
                {"title": "LOUIS VUITTON LV Malletage Round Sunglasses", "thumbnail_url": f"{R2}/items/ca918bb1-3561-4e7f-92e/thumb3.jpg", "metadata": {"brand": "LOUIS VUITTON", "category": "Eyewear"}, "description": "Quilted trunk pattern on round frames — LV heritage"},
            ],
        },
        {
            "artist_name": "lisa",
            "group_name": "BLACKPINK",
            "image_url": f"{R2}/blackpinkk.style/2024-08-31_10-59-45/2024-08-31_10-59-45_UTC_2.jpg",
            "solutions": [
                {"title": "Coperni Stripped Cropped Shirt", "thumbnail_url": f"{R2}/items/b4e01ff6-ef2a-463a-8ae/thumb.jpg", "metadata": {"brand": "Coperni", "category": "Tops"}, "description": "Deconstructed cropped shirt — avant-garde Paris"},
                {"title": "Chrome Hearts Leather Cross Patch Blue Mini Bowling Bag", "thumbnail_url": f"{R2}/items/b4e01ff6-ef2a-463a-8ae/thumb2.jpg", "metadata": {"brand": "Chrome Hearts", "category": "Bags"}, "description": "Rock'n'roll luxury mini bag — collector's item"},
                {"title": "BVLGARI Serpenti Viper Ring", "thumbnail_url": f"{R2}/items/b4e01ff6-ef2a-463a-8ae/thumb3.jpg", "metadata": {"brand": "BVLGARI", "category": "Jewelry"}, "description": "Snake-inspired pavé ring — bold Italian glamour"},
            ],
        },
    ],
}

# ──────────────────────────────────────────────
# Scenario 3: Rosé x SAINT LAURENT — Old Money New Wave
# ──────────────────────────────────────────────
SCENARIO_3 = {
    "seed_keyword": "로제 SAINT LAURENT 올드머니",
    "category": "fashion",
    "curated_topics": [
        {
            "keyword": "로제 SAINT LAURENT 올드머니",
            "trend_background": (
                "BLACKPINK 로제는 SAINT LAURENT과 TIFFANY & Co.를 축으로 "
                "'올드머니' 트렌드의 K-POP 대표 아이콘이다. "
                "캐시미어 스웨터에 THE ROW 데님, NY Yankees 캡을 매치하는 "
                "절묘한 하이-로우 믹스가 특징이다. Brandy Melville 같은 캐주얼 브랜드도 "
                "그녀가 입으면 럭셔리하게 변신한다."
            ),
            "related_keywords": ["old money aesthetic", "TIFFANY", "THE ROW", "high-low mix", "Parisian chic"],
        },
    ],
    "enriched_contexts": [
        {
            "artist_name": "rose",
            "group_name": "BLACKPINK",
            "image_url": f"{R2}/blackpinkk.style/2024-04-17_15-29-13/2024-04-17_15-29-13_UTC_5.jpg",
            "solutions": [
                {"title": "SAINT LAURENT Cashmere Sweater", "thumbnail_url": f"{R2}/items/2d184230-dcc9-466c-9d1/thumb.jpg", "metadata": {"brand": "SAINT LAURENT", "category": "Tops"}, "description": "Pure cashmere crewneck — timeless Parisian staple"},
                {"title": "THE ROW Domino Bag", "thumbnail_url": f"{R2}/items/2d184230-dcc9-466c-9d1/thumb2.jpg", "metadata": {"brand": "THE ROW", "category": "Bags"}, "description": "Minimalist structured bag by the Olsen twins' label"},
                {"title": "New Era NY Yankees Dark Navy", "thumbnail_url": f"{R2}/items/2d184230-dcc9-466c-9d1/thumb3.jpg", "metadata": {"brand": "New Era", "category": "Accessories"}, "description": "Classic baseball cap — the ultimate casual-luxe topper"},
                {"title": "THE ROW Carlton Jeans", "thumbnail_url": f"{R2}/items/2d184230-dcc9-466c-9d1/thumb4.jpg", "metadata": {"brand": "THE ROW", "category": "Bottoms"}, "description": "High-waisted straight-leg denim — understated perfection"},
                {"title": "SAINT LAURENT SL M94", "thumbnail_url": f"{R2}/items/2d184230-dcc9-466c-9d1/thumb5.jpg", "metadata": {"brand": "SAINT LAURENT", "category": "Eyewear"}, "description": "Oversized cat-eye sunglasses — French Riviera energy"},
            ],
        },
        {
            "artist_name": "rose",
            "group_name": "BLACKPINK",
            "image_url": f"{R2}/blackpinkk.style/2024-09-10_17-24-12/2024-09-10_17-24-12_UTC_4.jpg",
            "solutions": [
                {"title": "TIFFANY & Co. Elsa Peretti Bone Ring", "thumbnail_url": f"{R2}/items/db78b0e0-d2c5-416d-a3e/thumb.jpg", "metadata": {"brand": "TIFFANY & Co.", "category": "Jewelry"}, "description": "Organic sculptural ring — art meets fine jewelry"},
                {"title": "Brandy Melville Christy Hoodie", "thumbnail_url": f"{R2}/items/db78b0e0-d2c5-416d-a3e/thumb2.jpg", "metadata": {"brand": "Brandy Melville", "category": "Tops"}, "description": "Oversized Y2K hoodie — Gen Z casual staple"},
                {"title": "R13 Multi-Pocket Utility Pant", "thumbnail_url": f"{R2}/items/db78b0e0-d2c5-416d-a3e/thumb3.jpg", "metadata": {"brand": "R13", "category": "Bottoms"}, "description": "Utilitarian cargo pants — luxe workwear influence"},
                {"title": "SAINT LAURENT SL M94 Sunglasses", "thumbnail_url": f"{R2}/items/db78b0e0-d2c5-416d-a3e/thumb4.jpg", "metadata": {"brand": "SAINT LAURENT", "category": "Eyewear"}, "description": "Signature cat-eye — Rosé's go-to eyewear"},
            ],
        },
        {
            "artist_name": "rose",
            "group_name": "BLACKPINK",
            "image_url": f"{R2}/blackpinkk.style/2024-02-25_04-56-24/2024-02-25_04-56-24_UTC_5.jpg",
            "solutions": [
                {"title": "SAINT LAURENT Oversized Jacket in Lambskin", "thumbnail_url": f"{R2}/items/rose-2024-02/thumb.jpg", "metadata": {"brand": "SAINT LAURENT", "category": "Outerwear"}, "description": "Butter-soft lambskin oversized jacket — rock'n'roll heritage"},
                {"title": "BLACKPINK World Tour Dad Cap", "thumbnail_url": f"{R2}/items/rose-2024-02/thumb2.jpg", "metadata": {"brand": "BLACKPINK", "category": "Accessories"}, "description": "Tour merch cap — self-branding at its finest"},
            ],
        },
    ],
}

# ──────────────────────────────────────────────
# Scenario 4: Jisoo x Cartier & DIOR — Jewelry Completes the Look
# ──────────────────────────────────────────────
SCENARIO_4 = {
    "seed_keyword": "지수 Cartier DIOR 주얼리 스타일링",
    "category": "fashion",
    "curated_topics": [
        {
            "keyword": "지수 Cartier DIOR 주얼리 스타일링",
            "trend_background": (
                "BLACKPINK 지수는 Cartier Trinity 컬렉션과 DIOR 백으로 "
                "'주얼리가 완성하는 스타일'의 교과서를 쓰고 있다. "
                "alo yoga 애슬레저에 Cartier 네크리스를 레이어링하거나, "
                "LEMAIRE 크루아상 백과 코지한 루즈핏을 매치하는 센스가 돋보인다. "
                "캐주얼한 베이스에 하이주얼리를 더해 품격을 높이는 '엘레강스 캐주얼'의 아이콘."
            ),
            "related_keywords": ["Cartier Trinity", "DIOR", "jewelry styling", "athleisure luxe", "LEMAIRE"],
        },
    ],
    "enriched_contexts": [
        {
            "artist_name": "jisoo",
            "group_name": "BLACKPINK",
            "image_url": f"{R2}/blackpinkk.style/2024-03-24_08-15-22/2024-03-24_08-15-22_UTC_5.jpg",
            "solutions": [
                {"title": "Cartier Trinity Necklace", "thumbnail_url": f"{R2}/items/jisoo-2024-03/thumb.jpg", "metadata": {"brand": "Cartier", "category": "Jewelry"}, "description": "Three-gold interlocking ring necklace — Cartier's icon"},
                {"title": "Cartier Trinity Ring", "thumbnail_url": f"{R2}/items/jisoo-2024-03/thumb2.jpg", "metadata": {"brand": "Cartier", "category": "Jewelry"}, "description": "Tri-color rolling ring — eternal elegance"},
                {"title": "alo Cropped Cozy Day Full Zip Jacket", "thumbnail_url": f"{R2}/items/jisoo-2024-03/thumb3.jpg", "metadata": {"brand": "alo", "category": "Outerwear"}, "description": "Sherpa zip-up — athleisure comfort meets luxe jewelry"},
                {"title": "alo High-Waist Cozy Day Wide Pant", "thumbnail_url": f"{R2}/items/jisoo-2024-03/thumb4.jpg", "metadata": {"brand": "alo", "category": "Bottoms"}, "description": "Wide-leg cozy pants — airport lounge vibes"},
            ],
        },
        {
            "artist_name": "jisoo",
            "group_name": "BLACKPINK",
            "image_url": f"{R2}/blackpinkk.style/2024-05-28_04-22-15/2024-05-28_04-22-15_UTC_3.jpg",
            "solutions": [
                {"title": "LEMAIRE Large Croissant Bag (Soft Nappa Leather)", "thumbnail_url": f"{R2}/items/jisoo-2024-05/thumb.jpg", "metadata": {"brand": "LEMAIRE", "category": "Bags"}, "description": "Buttery nappa leather half-moon bag — French minimalism"},
                {"title": "alo Routine Cropped Zip Hoodie", "thumbnail_url": f"{R2}/items/jisoo-2024-05/thumb2.jpg", "metadata": {"brand": "alo", "category": "Tops"}, "description": "Cropped hoodie — casual base for jewelry focus"},
                {"title": "alo High-Waist Night Out Cargo Trouser", "thumbnail_url": f"{R2}/items/jisoo-2024-05/thumb3.jpg", "metadata": {"brand": "alo", "category": "Bottoms"}, "description": "Elevated cargo pants — utility chic"},
            ],
        },
        {
            "artist_name": "jisoo",
            "group_name": "BLACKPINK",
            "image_url": f"{R2}/blackpinkk.style/2024-09-04_06-33-18/2024-09-04_06-33-18_UTC_2.jpg",
            "solutions": [
                {"title": "DIOR Miss Dior Flap Bag", "thumbnail_url": f"{R2}/items/jisoo-2024-09/thumb.jpg", "metadata": {"brand": "DIOR", "category": "Bags"}, "description": "Cannage-quilted iconic flap — DIOR's signature"},
                {"title": "Cartier Tank Louis Watch", "thumbnail_url": f"{R2}/items/jisoo-2024-09/thumb2.jpg", "metadata": {"brand": "Cartier", "category": "Watch"}, "description": "Art Deco rectangular watch — horological icon"},
                {"title": "Chrome Hearts Triple Cross Beanie", "thumbnail_url": f"{R2}/items/jisoo-2024-09/thumb3.jpg", "metadata": {"brand": "Chrome Hearts", "category": "Accessories"}, "description": "Gothic luxury beanie — edge meets heritage"},
            ],
        },
    ],
}

# ──────────────────────────────────────────────
# Scenario 5: Danielle x Street — NewJeans Casual Sensibility
# ──────────────────────────────────────────────
SCENARIO_5 = {
    "seed_keyword": "다니엘 뉴진스 캐주얼 스트릿",
    "category": "fashion",
    "curated_topics": [
        {
            "keyword": "다니엘 뉴진스 캐주얼 스트릿",
            "trend_background": (
                "NewJeans 다니엘은 NIKE, BAPE, CELINE을 자유롭게 넘나드는 "
                "10대 특유의 발랄한 스트릿 감성으로 사랑받고 있다. "
                "새틴 봄버 재킷에 에어맥스, 플라워 캡과 캐릭터 마스코트까지 — "
                "하이엔드와 플레이풀함의 경계를 자유롭게 오가는 그녀의 스타일은 "
                "Z세대 캐주얼의 새로운 기준이 되었다."
            ),
            "related_keywords": ["Gen Z casual", "NIKE", "CELINE", "playful style", "teen fashion icon"],
        },
    ],
    "enriched_contexts": [
        {
            "artist_name": "danielle",
            "group_name": "NewJeans",
            "image_url": f"{R2}/newjeanscloset/2024-02-03_06-00-00/2024-02-03_06-00-00_UTC_3.jpg",
            "solutions": [
                {"title": "NIKE Dugout Loose Satin Jacket", "thumbnail_url": f"{R2}/items/danielle-2024-02/thumb.jpg", "metadata": {"brand": "NIKE", "category": "Outerwear"}, "description": "Retro satin bomber — sporty nostalgia"},
                {"title": "DEW E DEW E Flower Cap_Beige", "thumbnail_url": f"{R2}/items/danielle-2024-02/thumb2.jpg", "metadata": {"brand": "DEW E DEW E", "category": "Accessories"}, "description": "Floral embroidered cap — cute K-fashion accent"},
                {"title": "Asamimichan Face Stuffed Mascot", "thumbnail_url": f"{R2}/items/danielle-2024-02/thumb3.jpg", "metadata": {"brand": "Asamimichan", "category": "Lifestyle"}, "description": "Japanese character mascot — Gen Z kawaii culture"},
                {"title": "NIKE Air Max 90 LV8", "thumbnail_url": f"{R2}/items/danielle-2024-02/thumb4.jpg", "metadata": {"brand": "NIKE", "category": "Shoes"}, "description": "Air Max 90 — classic sneaker culture icon"},
            ],
        },
        {
            "artist_name": "danielle",
            "group_name": "NewJeans",
            "image_url": f"{R2}/newjeanscloset/2024-08-03_04-00-00/2024-08-03_04-00-00_UTC_2.jpg",
            "solutions": [
                {"title": "CELINE Slides", "thumbnail_url": f"{R2}/items/danielle-2024-08/thumb.jpg", "metadata": {"brand": "CELINE", "category": "Shoes"}, "description": "Triomphe logo slides — luxury loungewear essential"},
                {"title": "CELINE Loose Celine Paris T-Shirt", "thumbnail_url": f"{R2}/items/danielle-2024-08/thumb2.jpg", "metadata": {"brand": "CELINE", "category": "Tops"}, "description": "Oversized logo tee — French streetwear fusion"},
                {"title": "LANG & LU Loves Bunny T-Shirts", "thumbnail_url": f"{R2}/items/danielle-2024-08/thumb3.jpg", "metadata": {"brand": "LANG & LU", "category": "Tops"}, "description": "Bunny graphic tee — playful indie vibes"},
                {"title": "Wiggle Wiggle Smile We Love Cushion Blanket", "thumbnail_url": f"{R2}/items/danielle-2024-08/thumb4.jpg", "metadata": {"brand": "Wiggle Wiggle", "category": "Lifestyle"}, "description": "Character blanket — cozy lifestyle content"},
            ],
        },
        {
            "artist_name": "danielle",
            "group_name": "NewJeans",
            "image_url": f"{R2}/newjeanscloset/2024-06-21_03-00-00/2024-06-21_03-00-00_UTC_4.jpg",
            "solutions": [
                {"title": "BAPE x Alpha Industries Shark Full Zip Hoodie", "thumbnail_url": f"{R2}/items/danielle-2024-06/thumb.jpg", "metadata": {"brand": "BAPE x Alpha Industries", "category": "Outerwear"}, "description": "Military x street collab hoodie — hype culture staple"},
                {"title": "Pintuck Cargo Denim Pants", "thumbnail_url": f"{R2}/items/danielle-2024-06/thumb2.jpg", "metadata": {"brand": "Unknown", "category": "Bottoms"}, "description": "Cargo denim hybrid — utility meets Y2K"},
                {"title": "NewJeans Club Cap", "thumbnail_url": f"{R2}/items/danielle-2024-06/thumb3.jpg", "metadata": {"brand": "NewJeans", "category": "Accessories"}, "description": "Official merch cap — fandom x fashion crossover"},
            ],
        },
    ],
}

# ──────────────────────────────────────────────
# Scenario 6: Jennie vs Lisa — BLACKPINK Style Battle
# ──────────────────────────────────────────────
SCENARIO_6 = {
    "seed_keyword": "제니 vs 리사 스타일 배틀",
    "category": "fashion",
    "curated_topics": [
        {
            "keyword": "제니 vs 리사 BLACKPINK 스타일 배틀",
            "trend_background": (
                "BLACKPINK의 투톱 패션 아이콘, 제니와 리사. "
                "제니는 FOUNDRÆ 파인주얼리와 Supreme 캡으로 '하이-스트릿 믹스'를, "
                "리사는 자신의 브랜드 LLOUD와 Christian Louboutin으로 '셀럽 앙트레프러너' "
                "스타일을 보여준다. 같은 그룹이지만 완전히 다른 두 패션 세계관의 대결."
            ),
            "related_keywords": ["style battle", "BLACKPINK fashion", "FOUNDRÆ", "LLOUD", "K-pop rivalry"],
        },
    ],
    "enriched_contexts": [
        {
            "artist_name": "jennie",
            "group_name": "BLACKPINK",
            "image_url": f"{R2}/blackpinkk.style/2025-07-18_04-23-11/2025-07-18_04-23-11_UTC_3.jpg",
            "solutions": [
                {"title": "FOUNDRÆ Pave Diamond Initial - Heart Beat Super Fine", "thumbnail_url": f"{R2}/items/33d03380-3511-4fd2-b21/thumb.jpg", "metadata": {"brand": "FOUNDRÆ", "category": "Jewelry"}, "description": "Pave diamond initial pendant — personalized fine jewelry"},
                {"title": "FOUNDRÆ Protection - Thin Champleve Enamel Band", "thumbnail_url": f"{R2}/items/33d03380-3511-4fd2-b21/thumb2.jpg", "metadata": {"brand": "FOUNDRÆ", "category": "Jewelry"}, "description": "Enamel band ring — symbolic protection motif"},
                {"title": "Supreme Waxed Wool 6-Panel", "thumbnail_url": f"{R2}/items/760a16d4-40ba-4e12-aae/thumb.jpg", "metadata": {"brand": "Supreme", "category": "Accessories"}, "description": "Waxed wool cap — streetwear royalty status"},
                {"title": "young n sang Snowflake Vest", "thumbnail_url": f"{R2}/items/760a16d4-40ba-4e12-aae/thumb2.jpg", "metadata": {"brand": "young n sang", "category": "Outerwear"}, "description": "Knit vest — Korean indie designer piece"},
                {"title": "FOUNDRÆ Belcher Chain Necklace - Reverie", "thumbnail_url": f"{R2}/items/760a16d4-40ba-4e12-aae/thumb3.jpg", "metadata": {"brand": "FOUNDRÆ", "category": "Jewelry"}, "description": "Heavy chain necklace — bold statement piece"},
            ],
        },
        {
            "artist_name": "lisa",
            "group_name": "BLACKPINK",
            "image_url": f"{R2}/blackpinkk.style/2025-09-15_22-18-58/2025-09-15_22-18-58_UTC_9.jpg",
            "solutions": [
                {"title": "Christian Louboutin Cassia Lace Up", "thumbnail_url": f"{R2}/items/2a86ccad-e969-4025-b1a/thumb.jpg", "metadata": {"brand": "Christian Louboutin", "category": "Shoes"}, "description": "Red-soled lace-up boots — power dressing icon"},
                {"title": "ROJANATORN Baifern Necklace", "thumbnail_url": f"{R2}/items/93990dc6-7c08-4c48-86a/thumb.jpg", "metadata": {"brand": "ROJANATORN", "category": "Jewelry"}, "description": "Thai designer necklace — Lisa's heritage nod"},
            ],
        },
        {
            "artist_name": "lisa",
            "group_name": "BLACKPINK",
            "image_url": f"{R2}/blackpinkk.style/2025-09-12_00-14-53/2025-09-12_00-14-53_UTC_12.jpg",
            "solutions": [
                {"title": "LLOUD Light Pink Crop Tee", "thumbnail_url": f"{R2}/items/bf0de85f-6565-4e1e-beb/thumb.jpg", "metadata": {"brand": "LLOUD", "category": "Tops"}, "description": "Lisa's own brand — minimalist crop tee"},
                {"title": "LLOUD Light Pink Shorts", "thumbnail_url": f"{R2}/items/bf0de85f-6565-4e1e-beb/thumb2.jpg", "metadata": {"brand": "LLOUD", "category": "Bottoms"}, "description": "Matching shorts — coordinated set dressing"},
                {"title": "DEADLINE Embroidered Logo Ballcap", "thumbnail_url": f"{R2}/items/bf0de85f-6565-4e1e-beb/thumb3.jpg", "metadata": {"brand": "DEADLINE", "category": "Accessories"}, "description": "Thai streetwear cap — supporting local brands"},
            ],
        },
    ],
}

# ──────────────────────────────────────────────
# Scenario 7: K-POP Airport Fashion Crossover — 4th Gen Icons
# ──────────────────────────────────────────────
SCENARIO_7 = {
    "seed_keyword": "K-POP 공항패션 크로스오버",
    "category": "fashion",
    "curated_topics": [
        {
            "keyword": "K-POP 공항패션 크로스오버",
            "trend_background": (
                "K-POP 4세대 아이콘들의 공항패션은 그 자체로 하나의 패션쇼다. "
                "제니의 DSQUARED2 모헤어 니트와 CHANEL 네크리스 레이어링, "
                "리사의 LOEWE 롱슬리브와 LV 캡의 믹스매치, "
                "지수의 R13 레오파드 셔츠와 courrèges 와이드 팬츠의 빈티지 무드까지. "
                "공항이라는 무대에서 펼쳐지는 K-POP 스타일의 다양성을 조명한다."
            ),
            "related_keywords": ["airport fashion", "K-pop style", "travel outfit", "4th gen", "paparazzi fashion"],
        },
    ],
    "enriched_contexts": [
        {
            "artist_name": "jennie",
            "group_name": "BLACKPINK",
            "image_url": f"{R2}/blackpinkk.style/2024-10-13_21-44-28/2024-10-13_21-44-28_UTC_8.jpg",
            "solutions": [
                {"title": "DSQUARED2 Mohair Mini Cape Knit", "thumbnail_url": f"{R2}/items/1adb63fc-738b-47c6-802/thumb.jpg", "metadata": {"brand": "DSQUARED2", "category": "Tops"}, "description": "Mohair cape knit — cozy luxury for transit"},
                {"title": "CHANEL Long Necklace", "thumbnail_url": f"{R2}/items/1adb63fc-738b-47c6-802/thumb2.jpg", "metadata": {"brand": "CHANEL", "category": "Jewelry"}, "description": "Pearl and chain long necklace — layered elegance"},
                {"title": "CHANEL Necklace", "thumbnail_url": f"{R2}/items/1adb63fc-738b-47c6-802/thumb3.jpg", "metadata": {"brand": "CHANEL", "category": "Jewelry"}, "description": "Short chain necklace — double Chanel layering"},
            ],
        },
        {
            "artist_name": "lisa",
            "group_name": "BLACKPINK",
            "image_url": f"{R2}/blackpinkk.style/2024-05-09_08-45-22/2024-05-09_08-45-22_UTC_3.jpg",
            "solutions": [
                {"title": "LOEWE Long Sleeve T-shirt", "thumbnail_url": f"{R2}/items/lisa-2024-05/thumb.jpg", "metadata": {"brand": "LOEWE", "category": "Tops"}, "description": "Anagram logo long sleeve — Spanish luxury casual"},
                {"title": "LOUIS VUITTON LV Day Cap", "thumbnail_url": f"{R2}/items/lisa-2024-05/thumb2.jpg", "metadata": {"brand": "LOUIS VUITTON", "category": "Accessories"}, "description": "Monogram cap — travel essential by LV"},
                {"title": "POP MART CRYBABY x Powerpuff Girls Series", "thumbnail_url": f"{R2}/items/lisa-2024-05/thumb3.jpg", "metadata": {"brand": "POP MART", "category": "Lifestyle"}, "description": "Designer toy — Lisa's collector side"},
            ],
        },
        {
            "artist_name": "jisoo",
            "group_name": "BLACKPINK",
            "image_url": f"{R2}/blackpinkk.style/2025-08-02_03-15-44/2025-08-02_03-15-44_UTC_5.jpg",
            "solutions": [
                {"title": "R13 Shredded Seam Drop Neck Shirt - Leopard", "thumbnail_url": f"{R2}/items/jisoo-2025-08/thumb.jpg", "metadata": {"brand": "R13", "category": "Tops"}, "description": "Distressed leopard shirt — punk-luxe statement"},
                {"title": "courrèges Baggy Wide-leg Twill Pants", "thumbnail_url": f"{R2}/items/jisoo-2025-08/thumb2.jpg", "metadata": {"brand": "courrèges", "category": "Bottoms"}, "description": "Retro-futuristic wide pants — 60s meets now"},
                {"title": "DIOR Medium Grand Tour Multipocket Bag", "thumbnail_url": f"{R2}/items/jisoo-2025-08/thumb3.jpg", "metadata": {"brand": "DIOR", "category": "Bags"}, "description": "Multi-pocket travel bag — functional luxury"},
                {"title": "DEADLINE WORLD TOUR Embroidered Logo Ballcap", "thumbnail_url": f"{R2}/items/jisoo-2025-08/thumb4.jpg", "metadata": {"brand": "DEADLINE", "category": "Accessories"}, "description": "Tour-themed cap — music x fashion synergy"},
            ],
        },
    ],
}

ALL_SCENARIOS = [
    ("인물: 제니 x Chloé 소프트럭셔리", SCENARIO_1),
    ("브랜드: 리사 x STELLA McCARTNEY", SCENARIO_2),
    ("취향: 로제 x SAINT LAURENT 올드머니", SCENARIO_3),
    ("아이템: 지수 x Cartier 주얼리", SCENARIO_4),
    ("스트릿: 다니엘 캐주얼 감성", SCENARIO_5),
    ("비교: 제니 vs 리사 스타일배틀", SCENARIO_6),
    ("크로스오버: K-POP 공항패션", SCENARIO_7),
]


# ──────────────────────────────────────────────
# Pipeline stubs (same as run_pipeline_fast.py)
# ──────────────────────────────────────────────

async def make_stub_curation(topics):
    async def stub(state):
        return {"curated_topics": topics}
    return stub

async def stub_design_spec(state):
    return {}

async def make_stub_source(contexts):
    async def stub(state):
        return {"enriched_contexts": contexts}
    return stub

async def stub_review(state):
    return {
        "review_result": {
            "passed": True,
            "criteria": [{"criterion": "skip", "passed": True, "reason": "Review skipped", "severity": "minor"}],
            "summary": "Auto-passed for testing.",
            "suggestions": [],
        },
        "pipeline_status": "awaiting_approval",
    }

async def auto_approve_admin_gate(state):
    from editorial_ai.services.content_service import save_pending_content
    current_draft = state.get("current_draft") or {}
    curation_input = state.get("curation_input") or {}
    review_result = state.get("review_result") or {}
    title = current_draft.get("title", "")
    keyword = curation_input.get("seed_keyword", "")
    review_summary = review_result.get("summary", "")
    thread_id = state.get("thread_id") or keyword or "unknown"
    saved = await save_pending_content(
        thread_id=thread_id, layout_json=current_draft,
        title=title, keyword=keyword, review_summary=review_summary,
    )
    content_id = saved.get("id", "")
    print(f"  Content saved: id={content_id}, title={title[:60]}", flush=True)
    return {"admin_decision": "approved", "current_draft_id": content_id, "pipeline_status": "awaiting_approval"}

async def stub_publish(state):
    from editorial_ai.services.content_service import update_content_status
    content_id = state.get("current_draft_id")
    if content_id:
        await update_content_status(content_id, "published")
    return {"pipeline_status": "published"}


async def run_scenario(label, scenario):
    from editorial_ai.graph import build_graph

    curation_stub = await make_stub_curation(scenario["curated_topics"])
    source_stub = await make_stub_source(scenario["enriched_contexts"])

    graph = build_graph(
        node_overrides={
            "curation": curation_stub,
            "design_spec": stub_design_spec,
            "source": source_stub,
            "review": stub_review,
            "admin_gate": auto_approve_admin_gate,
            "publish": stub_publish,
        }
    )

    thread_id = str(uuid.uuid4())
    initial_state = {
        "thread_id": thread_id,
        "curation_input": {
            "seed_keyword": scenario["seed_keyword"],
            "category": scenario["category"],
        },
    }

    start = time.time()
    print(f"\n{'='*60}", flush=True)
    print(f">>> [{label}] seed: {scenario['seed_keyword']}", flush=True)
    print(f">>> thread_id: {thread_id}", flush=True)
    print(f"{'='*60}", flush=True)

    try:
        result = await graph.ainvoke(initial_state)
        elapsed = time.time() - start
        draft = result.get("current_draft", {})
        blocks = draft.get("blocks", [])
        print(f"  Completed in {elapsed:.1f}s", flush=True)
        print(f"  Title: {draft.get('title', 'N/A')}", flush=True)
        print(f"  Blocks: {len(blocks)} — {', '.join(b.get('type','?') for b in blocks)}", flush=True)
        print(f"  Status: {result.get('pipeline_status')}", flush=True)
        return True
    except Exception as e:
        elapsed = time.time() - start
        print(f"  FAILED in {elapsed:.1f}s: {e}", flush=True)
        return False


async def main():
    from editorial_ai.services.content_service import list_contents

    total_start = time.time()
    _inject_urls(ALL_SCENARIOS)
    print(">>> Multi-scenario pipeline test (v3 — with solution URLs)", flush=True)
    print(f">>> Running {len(ALL_SCENARIOS)} scenarios sequentially", flush=True)

    results = []
    for label, scenario in ALL_SCENARIOS:
        ok = await run_scenario(label, scenario)
        results.append((label, ok))

    total_elapsed = time.time() - total_start
    print(f"\n{'='*60}", flush=True)
    print(f">>> All done in {total_elapsed:.1f}s", flush=True)
    print(f"{'='*60}", flush=True)

    for label, ok in results:
        status = "OK" if ok else "FAIL"
        print(f"  [{status}] {label}", flush=True)

    items = await list_contents()
    print(f"\n>>> Total saved contents: {len(items)}", flush=True)
    for item in items:
        print(f"  [{item['status']}] {item['title'][:60]}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
