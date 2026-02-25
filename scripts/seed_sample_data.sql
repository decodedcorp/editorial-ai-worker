-- Seed sample data for E2E pipeline testing
-- Usage: psql $DATABASE_URL -f scripts/seed_sample_data.sql
-- Or: Run via Supabase SQL Editor
-- Idempotent: safe to run multiple times (ON CONFLICT DO NOTHING)
--
-- Data covers: NewJeans, aespa, BLACKPINK, IVE, LE SSERAFIM
-- Brands: Gucci, Chanel, Dior, Miu Miu, Prada, Celine, Saint Laurent,
--         Ader Error, Andersson Bell, Gentle Monster, Thom Browne
--
-- Relationship: posts -> spots (post_id) -> solutions (spot_id)

-- ============================================================================
-- CELEBS (12 rows)
-- ============================================================================
INSERT INTO celebs (id, name, name_en, category, profile_image_url, description, tags) VALUES
  ('celeb-001', '민지',   'Minji',    'idol', 'https://images.example.com/celebs/minji.jpg',    'NewJeans 민지, 하이틴 패션 아이콘', '["NewJeans", "하이틴", "패션"]'::jsonb),
  ('celeb-002', '하니',   'Hanni',    'idol', 'https://images.example.com/celebs/hanni.jpg',    'NewJeans 하니, 글로벌 앰버서더', '["NewJeans", "Gucci"]'::jsonb),
  ('celeb-003', '카리나', 'Karina',   'idol', 'https://images.example.com/celebs/karina.jpg',   'aespa 카리나, 럭셔리 브랜드 뮤즈', '["aespa", "Prada"]'::jsonb),
  ('celeb-004', '윈터',   'Winter',   'idol', 'https://images.example.com/celebs/winter.jpg',   'aespa 윈터, 시크한 무드', '["aespa", "Miu Miu"]'::jsonb),
  ('celeb-005', '제니',   'Jennie',   'idol', 'https://images.example.com/celebs/jennie.jpg',   'BLACKPINK 제니, 패션 아이콘', '["BLACKPINK", "Chanel"]'::jsonb),
  ('celeb-006', '리사',   'Lisa',     'idol', 'https://images.example.com/celebs/lisa.jpg',     'BLACKPINK 리사, 글로벌 트렌드세터', '["BLACKPINK", "Celine"]'::jsonb),
  ('celeb-007', '장원영', 'Wonyoung', 'idol', 'https://images.example.com/celebs/wonyoung.jpg', 'IVE 장원영, MZ세대 패션 리더', '["IVE", "Miu Miu"]'::jsonb),
  ('celeb-008', '안유진', 'Yujin',    'idol', 'https://images.example.com/celebs/yujin.jpg',    'IVE 안유진, 상큼한 스타일', '["IVE", "Versace"]'::jsonb),
  ('celeb-009', '카즈하', 'Kazuha',   'idol', 'https://images.example.com/celebs/kazuha.jpg',   'LE SSERAFIM 카즈하, 우아한 무드', '["LE SSERAFIM", "Dior"]'::jsonb),
  ('celeb-010', '사쿠라', 'Sakura',   'idol', 'https://images.example.com/celebs/sakura.jpg',   'LE SSERAFIM 사쿠라, 유니크 스타일', '["LE SSERAFIM", "Saint Laurent"]'::jsonb),
  ('celeb-011', '로제',   'Rose',     'idol', 'https://images.example.com/celebs/rose.jpg',     'BLACKPINK 로제, 페미닌 시크', '["BLACKPINK", "Saint Laurent"]'::jsonb),
  ('celeb-012', '가을',   'Gaeul',    'idol', 'https://images.example.com/celebs/gaeul.jpg',    'IVE 가을, 뉴트로 감성', '["IVE", "Thom Browne"]'::jsonb)
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- POSTS (18 rows)
-- ============================================================================
INSERT INTO posts (id, image_url, media_type, title, artist_name, group_name, context, view_count, trending_score, status) VALUES
  -- NewJeans
  ('post-001', 'https://images.example.com/posts/post-001.jpg', 'image', '민지의 파리 패션위크 Chanel 룩',         '민지',   'NewJeans',     'fashion week',    42000, 95, 'active'),
  ('post-002', 'https://images.example.com/posts/post-002.jpg', 'image', '하니 Gucci 앰버서더 공항패션',           '하니',   'NewJeans',     'airport fashion',  38000, 92, 'active'),
  ('post-003', 'https://images.example.com/posts/post-003.jpg', 'image', '민지 x 하니 음방 출근길 스타일링',        '민지',   'NewJeans',     'music show',      25000, 78, 'active'),
  -- aespa
  ('post-004', 'https://images.example.com/posts/post-004.jpg', 'image', '카리나 Prada 밀라노 패션위크',           '카리나', 'aespa',        'fashion week',    45000, 97, 'active'),
  ('post-005', 'https://images.example.com/posts/post-005.jpg', 'image', '윈터 Miu Miu 매거진 화보',              '윈터',   'aespa',        'magazine shoot',  32000, 85, 'active'),
  ('post-006', 'https://images.example.com/posts/post-006.jpg', 'image', '카리나 브랜드 이벤트 올블랙 룩',          '카리나', 'aespa',        'brand event',     28000, 80, 'active'),
  -- BLACKPINK
  ('post-007', 'https://images.example.com/posts/post-007.jpg', 'image', '제니 Chanel 쿠튀르 쇼 프론트로',         '제니',   'BLACKPINK',    'fashion week',    50000, 99, 'active'),
  ('post-008', 'https://images.example.com/posts/post-008.jpg', 'image', '리사 Celine 글로벌 앰버서더 공항룩',      '리사',   'BLACKPINK',    'airport fashion',  47000, 96, 'active'),
  ('post-009', 'https://images.example.com/posts/post-009.jpg', 'image', '로제 Saint Laurent 매거진 커버',         '로제',   'BLACKPINK',    'magazine shoot',  40000, 93, 'active'),
  ('post-010', 'https://images.example.com/posts/post-010.jpg', 'image', '제니 효과 — 착용 후 품절 아이템 모음',    '제니',   'BLACKPINK',    'brand event',     35000, 88, 'active'),
  -- IVE
  ('post-011', 'https://images.example.com/posts/post-011.jpg', 'image', '장원영 Miu Miu 앰버서더 브랜드 이벤트',   '장원영', 'IVE',          'brand event',     36000, 90, 'active'),
  ('post-012', 'https://images.example.com/posts/post-012.jpg', 'image', '안유진 공항패션 캐주얼 코디',             '안유진', 'IVE',          'airport fashion',  22000, 72, 'active'),
  ('post-013', 'https://images.example.com/posts/post-013.jpg', 'image', '가을 Thom Browne 매거진 화보',          '가을',   'IVE',          'magazine shoot',  18000, 68, 'active'),
  -- LE SSERAFIM
  ('post-014', 'https://images.example.com/posts/post-014.jpg', 'image', '카즈하 Dior 서울 패션쇼',               '카즈하', 'LE SSERAFIM',  'fashion week',    33000, 86, 'active'),
  ('post-015', 'https://images.example.com/posts/post-015.jpg', 'image', '사쿠라 Saint Laurent 공항 출국',         '사쿠라', 'LE SSERAFIM',  'airport fashion',  20000, 70, 'active'),
  ('post-016', 'https://images.example.com/posts/post-016.jpg', 'image', '카즈하 x 사쿠라 음악방송 출근길',        '카즈하', 'LE SSERAFIM',  'music show',      15000, 62, 'active'),
  -- Cross-group / trending
  ('post-017', 'https://images.example.com/posts/post-017.jpg', 'image', 'K-패션 셀럽 Gentle Monster 선글라스 트렌드', '하니', 'NewJeans',    'brand event',     30000, 83, 'active'),
  ('post-018', 'https://images.example.com/posts/post-018.jpg', 'image', 'Ader Error x K-POP 콜라보 룩북',        '윈터',   'aespa',        'brand event',     27000, 79, 'active')
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- SPOTS (28 rows) — fashion items spotted in each post
-- ============================================================================
INSERT INTO spots (id, post_id) VALUES
  -- post-001 민지 Chanel fashion week (2 spots)
  ('spot-001', 'post-001'),
  ('spot-002', 'post-001'),
  -- post-002 하니 Gucci airport (2 spots)
  ('spot-003', 'post-002'),
  ('spot-004', 'post-002'),
  -- post-003 민지x하니 music show (1 spot)
  ('spot-005', 'post-003'),
  -- post-004 카리나 Prada fashion week (2 spots)
  ('spot-006', 'post-004'),
  ('spot-007', 'post-004'),
  -- post-005 윈터 Miu Miu magazine (1 spot)
  ('spot-008', 'post-005'),
  -- post-006 카리나 brand event (1 spot)
  ('spot-009', 'post-006'),
  -- post-007 제니 Chanel couture (2 spots)
  ('spot-010', 'post-007'),
  ('spot-011', 'post-007'),
  -- post-008 리사 Celine airport (2 spots)
  ('spot-012', 'post-008'),
  ('spot-013', 'post-008'),
  -- post-009 로제 Saint Laurent magazine (1 spot)
  ('spot-014', 'post-009'),
  -- post-010 제니 brand event (2 spots)
  ('spot-015', 'post-010'),
  ('spot-016', 'post-010'),
  -- post-011 장원영 Miu Miu brand event (2 spots)
  ('spot-017', 'post-011'),
  ('spot-018', 'post-011'),
  -- post-012 안유진 airport (1 spot)
  ('spot-019', 'post-012'),
  -- post-013 가을 Thom Browne magazine (1 spot)
  ('spot-020', 'post-013'),
  -- post-014 카즈하 Dior fashion week (2 spots)
  ('spot-021', 'post-014'),
  ('spot-022', 'post-014'),
  -- post-015 사쿠라 Saint Laurent airport (1 spot)
  ('spot-023', 'post-015'),
  -- post-016 카즈하x사쿠라 music show (1 spot)
  ('spot-024', 'post-016'),
  -- post-017 Gentle Monster trend (1 spot)
  ('spot-025', 'post-017'),
  -- post-018 Ader Error collab (2 spots)
  ('spot-026', 'post-018'),
  ('spot-027', 'post-018'),
  -- extra spot for coverage
  ('spot-028', 'post-012')
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- SOLUTIONS (28 rows) — product/brand matches for each spot
-- ============================================================================
INSERT INTO solutions (id, spot_id, title, thumbnail_url, metadata, link_type, original_url) VALUES
  -- spot-001: 민지 Chanel tweed jacket
  ('sol-001', 'spot-001', 'Chanel 트위드 재킷 2025 S/S',
   'https://images.example.com/solutions/chanel-tweed.jpg',
   '{"keywords": ["Chanel", "tweed", "jacket", "민지"], "qa_pairs": [{"question": "What brand is this?", "answer": "Chanel"}, {"question": "What is the product?", "answer": "Chanel 2025 S/S tweed jacket in pink"}]}'::jsonb,
   'product', 'https://www.chanel.com/example/tweed-jacket'),

  -- spot-002: 민지 Chanel bag
  ('sol-002', 'spot-002', 'Chanel Classic Flap Bag',
   'https://images.example.com/solutions/chanel-flap.jpg',
   '{"keywords": ["Chanel", "bag", "Classic Flap"], "qa_pairs": [{"question": "What brand is this?", "answer": "Chanel"}, {"question": "What is the product?", "answer": "Classic Flap medium in black caviar leather"}]}'::jsonb,
   'product', 'https://www.chanel.com/example/classic-flap'),

  -- spot-003: 하니 Gucci bag
  ('sol-003', 'spot-003', 'Gucci Jackie 1961 미니 숄더백',
   'https://images.example.com/solutions/gucci-jackie.jpg',
   '{"keywords": ["Gucci", "bag", "Jackie"], "qa_pairs": [{"question": "What brand is this?", "answer": "Gucci"}, {"question": "What is the product?", "answer": "Jackie 1961 mini shoulder bag in beige"}]}'::jsonb,
   'product', 'https://www.gucci.com/example/jackie-1961'),

  -- spot-004: 하니 Gucci sunglasses
  ('sol-004', 'spot-004', 'Gucci 라운드 선글라스',
   'https://images.example.com/solutions/gucci-sunglasses.jpg',
   '{"keywords": ["Gucci", "sunglasses", "round"], "qa_pairs": [{"question": "What brand is this?", "answer": "Gucci"}, {"question": "What is the product?", "answer": "Gucci round acetate sunglasses"}]}'::jsonb,
   'product', 'https://www.gucci.com/example/round-sunglasses'),

  -- spot-005: 민지x하니 Andersson Bell
  ('sol-005', 'spot-005', 'Andersson Bell 오버사이즈 블레이저',
   'https://images.example.com/solutions/andersson-blazer.jpg',
   '{"keywords": ["Andersson Bell", "blazer", "oversized"], "qa_pairs": [{"question": "What brand is this?", "answer": "Andersson Bell"}, {"question": "What is the product?", "answer": "Oversized deconstructed blazer"}]}'::jsonb,
   'brand', 'https://www.anderssonbell.com/example/blazer'),

  -- spot-006: 카리나 Prada bag
  ('sol-006', 'spot-006', 'Prada Re-Edition 2005 나일론 백',
   'https://images.example.com/solutions/prada-reedition.jpg',
   '{"keywords": ["Prada", "bag", "Re-Edition", "nylon"], "qa_pairs": [{"question": "What brand is this?", "answer": "Prada"}, {"question": "What is the product?", "answer": "Prada Re-Edition 2005 nylon shoulder bag in black"}]}'::jsonb,
   'product', 'https://www.prada.com/example/re-edition'),

  -- spot-007: 카리나 Prada shoes
  ('sol-007', 'spot-007', 'Prada 모놀리스 로퍼',
   'https://images.example.com/solutions/prada-monolith.jpg',
   '{"keywords": ["Prada", "shoes", "loafer", "Monolith"], "qa_pairs": [{"question": "What brand is this?", "answer": "Prada"}, {"question": "What is the product?", "answer": "Prada Monolith brushed leather loafers"}]}'::jsonb,
   'product', 'https://www.prada.com/example/monolith-loafer'),

  -- spot-008: 윈터 Miu Miu dress
  ('sol-008', 'spot-008', 'Miu Miu 크리스탈 미니드레스',
   'https://images.example.com/solutions/miumiu-crystal.jpg',
   '{"keywords": ["Miu Miu", "dress", "crystal", "mini"], "qa_pairs": [{"question": "What brand is this?", "answer": "Miu Miu"}, {"question": "What is the product?", "answer": "Crystal-embellished mini dress"}]}'::jsonb,
   'product', 'https://www.miumiu.com/example/crystal-dress'),

  -- spot-009: 카리나 all-black brand event
  ('sol-009', 'spot-009', 'Prada 나일론 크로스바디백',
   'https://images.example.com/solutions/prada-crossbody.jpg',
   '{"keywords": ["Prada", "bag", "crossbody", "nylon"], "qa_pairs": [{"question": "What brand is this?", "answer": "Prada"}, {"question": "What is the product?", "answer": "Prada nylon crossbody bag in black"}]}'::jsonb,
   'product', 'https://www.prada.com/example/crossbody'),

  -- spot-010: 제니 Chanel couture dress
  ('sol-010', 'spot-010', 'Chanel 쿠튀르 트위드 드레스',
   'https://images.example.com/solutions/chanel-couture-dress.jpg',
   '{"keywords": ["Chanel", "dress", "couture", "tweed"], "qa_pairs": [{"question": "What brand is this?", "answer": "Chanel"}, {"question": "What is the product?", "answer": "Chanel Haute Couture tweed mini dress"}]}'::jsonb,
   'product', 'https://www.chanel.com/example/couture-dress'),

  -- spot-011: 제니 Chanel jewelry
  ('sol-011', 'spot-011', 'Chanel 까멜리아 이어링',
   'https://images.example.com/solutions/chanel-camellia.jpg',
   '{"keywords": ["Chanel", "jewelry", "earring", "camellia"], "qa_pairs": [{"question": "What brand is this?", "answer": "Chanel"}, {"question": "What is the product?", "answer": "Chanel Camellia drop earrings in gold"}]}'::jsonb,
   'product', 'https://www.chanel.com/example/camellia-earring'),

  -- spot-012: 리사 Celine bag
  ('sol-012', 'spot-012', 'Celine 트리오페 백',
   'https://images.example.com/solutions/celine-triomphe.jpg',
   '{"keywords": ["Celine", "bag", "Triomphe"], "qa_pairs": [{"question": "What brand is this?", "answer": "Celine"}, {"question": "What is the product?", "answer": "Celine Triomphe shoulder bag in tan"}]}'::jsonb,
   'product', 'https://www.celine.com/example/triomphe'),

  -- spot-013: 리사 Celine sunglasses
  ('sol-013', 'spot-013', 'Celine 캣아이 선글라스',
   'https://images.example.com/solutions/celine-cateye.jpg',
   '{"keywords": ["Celine", "sunglasses", "cat-eye"], "qa_pairs": [{"question": "What brand is this?", "answer": "Celine"}, {"question": "What is the product?", "answer": "Celine cat-eye acetate sunglasses in black"}]}'::jsonb,
   'product', 'https://www.celine.com/example/cateye-sunglasses'),

  -- spot-014: 로제 Saint Laurent jacket
  ('sol-014', 'spot-014', 'Saint Laurent 레더 바이커 재킷',
   'https://images.example.com/solutions/ysl-biker.jpg',
   '{"keywords": ["Saint Laurent", "jacket", "leather", "biker"], "qa_pairs": [{"question": "What brand is this?", "answer": "Saint Laurent"}, {"question": "What is the product?", "answer": "Saint Laurent leather biker jacket"}]}'::jsonb,
   'product', 'https://www.ysl.com/example/biker-jacket'),

  -- spot-015: 제니 Chanel shoes
  ('sol-015', 'spot-015', 'Chanel 슬링백 펌프스',
   'https://images.example.com/solutions/chanel-slingback.jpg',
   '{"keywords": ["Chanel", "shoes", "slingback", "pumps"], "qa_pairs": [{"question": "What brand is this?", "answer": "Chanel"}, {"question": "What is the product?", "answer": "Chanel two-tone slingback pumps"}]}'::jsonb,
   'product', 'https://www.chanel.com/example/slingback'),

  -- spot-016: 제니 효과 brand reference
  ('sol-016', 'spot-016', 'Jennie Effect 착용 아이템 레퍼런스',
   'https://images.example.com/solutions/jennie-effect.jpg',
   '{"keywords": ["Jennie", "effect", "sold out", "trend"], "qa_pairs": [{"question": "Why is this trending?", "answer": "Jennie''s wear drives instant sellout"}, {"question": "Which items?", "answer": "Chanel slingback pumps and micro bag"}]}'::jsonb,
   'reference', 'https://editorial.example.com/jennie-effect'),

  -- spot-017: 장원영 Miu Miu bag
  ('sol-017', 'spot-017', 'Miu Miu 와너 숄더백',
   'https://images.example.com/solutions/miumiu-wander.jpg',
   '{"keywords": ["Miu Miu", "bag", "Wander"], "qa_pairs": [{"question": "What brand is this?", "answer": "Miu Miu"}, {"question": "What is the product?", "answer": "Miu Miu Wander matelasse shoulder bag in pink"}]}'::jsonb,
   'product', 'https://www.miumiu.com/example/wander'),

  -- spot-018: 장원영 Miu Miu shoes
  ('sol-018', 'spot-018', 'Miu Miu 발레리나 플랫',
   'https://images.example.com/solutions/miumiu-ballet.jpg',
   '{"keywords": ["Miu Miu", "shoes", "ballet", "flat"], "qa_pairs": [{"question": "What brand is this?", "answer": "Miu Miu"}, {"question": "What is the product?", "answer": "Miu Miu satin ballet flats with crystal buckle"}]}'::jsonb,
   'product', 'https://www.miumiu.com/example/ballet-flat'),

  -- spot-019: 안유진 casual airport
  ('sol-019', 'spot-019', 'Ader Error 오버핏 후디',
   'https://images.example.com/solutions/adererror-hoodie.jpg',
   '{"keywords": ["Ader Error", "hoodie", "oversized", "casual"], "qa_pairs": [{"question": "What brand is this?", "answer": "Ader Error"}, {"question": "What is the product?", "answer": "Ader Error oversized logo hoodie in grey"}]}'::jsonb,
   'brand', 'https://www.adererror.com/example/hoodie'),

  -- spot-020: 가을 Thom Browne
  ('sol-020', 'spot-020', 'Thom Browne 카디건 드레스',
   'https://images.example.com/solutions/thombrowne-cardigan.jpg',
   '{"keywords": ["Thom Browne", "dress", "cardigan", "preppy"], "qa_pairs": [{"question": "What brand is this?", "answer": "Thom Browne"}, {"question": "What is the product?", "answer": "Thom Browne knit cardigan dress with grosgrain trim"}]}'::jsonb,
   'product', 'https://www.thombrowne.com/example/cardigan-dress'),

  -- spot-021: 카즈하 Dior bag
  ('sol-021', 'spot-021', 'Dior Lady Dior 미니백',
   'https://images.example.com/solutions/dior-ladydior.jpg',
   '{"keywords": ["Dior", "bag", "Lady Dior", "mini"], "qa_pairs": [{"question": "What brand is this?", "answer": "Dior"}, {"question": "What is the product?", "answer": "Lady Dior mini bag in powder pink lambskin"}]}'::jsonb,
   'product', 'https://www.dior.com/example/lady-dior'),

  -- spot-022: 카즈하 Dior shoes
  ('sol-022', 'spot-022', 'Dior J''Adior 슬링백',
   'https://images.example.com/solutions/dior-jadior.jpg',
   '{"keywords": ["Dior", "shoes", "slingback", "J''Adior"], "qa_pairs": [{"question": "What brand is this?", "answer": "Dior"}, {"question": "What is the product?", "answer": "Dior J''Adior slingback in nude patent"}]}'::jsonb,
   'product', 'https://www.dior.com/example/jadior-slingback'),

  -- spot-023: 사쿠라 Saint Laurent bag
  ('sol-023', 'spot-023', 'Saint Laurent 루루 백',
   'https://images.example.com/solutions/ysl-loulou.jpg',
   '{"keywords": ["Saint Laurent", "bag", "Loulou"], "qa_pairs": [{"question": "What brand is this?", "answer": "Saint Laurent"}, {"question": "What is the product?", "answer": "Saint Laurent Loulou small chain bag in black"}]}'::jsonb,
   'product', 'https://www.ysl.com/example/loulou'),

  -- spot-024: 카즈하x사쿠라 music show
  ('sol-024', 'spot-024', 'Andersson Bell 크롭 니트',
   'https://images.example.com/solutions/andersson-knit.jpg',
   '{"keywords": ["Andersson Bell", "knit", "crop"], "qa_pairs": [{"question": "What brand is this?", "answer": "Andersson Bell"}, {"question": "What is the product?", "answer": "Andersson Bell asymmetric crop knit top"}]}'::jsonb,
   'brand', 'https://www.anderssonbell.com/example/crop-knit'),

  -- spot-025: Gentle Monster sunglasses trend
  ('sol-025', 'spot-025', 'Gentle Monster Jentle Garden 선글라스',
   'https://images.example.com/solutions/gm-jentle.jpg',
   '{"keywords": ["Gentle Monster", "sunglasses", "Jentle Garden"], "qa_pairs": [{"question": "What brand is this?", "answer": "Gentle Monster"}, {"question": "What is the product?", "answer": "Gentle Monster x Jentle Garden oversized sunglasses"}]}'::jsonb,
   'product', 'https://www.gentlemonster.com/example/jentle-garden'),

  -- spot-026: Ader Error collab jacket
  ('sol-026', 'spot-026', 'Ader Error 패딩 봄버 재킷',
   'https://images.example.com/solutions/adererror-bomber.jpg',
   '{"keywords": ["Ader Error", "jacket", "bomber", "padded"], "qa_pairs": [{"question": "What brand is this?", "answer": "Ader Error"}, {"question": "What is the product?", "answer": "Ader Error padded bomber jacket in navy"}]}'::jsonb,
   'brand', 'https://www.adererror.com/example/bomber'),

  -- spot-027: Ader Error collab bag
  ('sol-027', 'spot-027', 'Ader Error 크로스바디 백',
   'https://images.example.com/solutions/adererror-crossbody.jpg',
   '{"keywords": ["Ader Error", "bag", "crossbody"], "qa_pairs": [{"question": "What brand is this?", "answer": "Ader Error"}, {"question": "What is the product?", "answer": "Ader Error nylon crossbody bag in black"}]}'::jsonb,
   'brand', 'https://www.adererror.com/example/crossbody'),

  -- spot-028: 안유진 airport shoes
  ('sol-028', 'spot-028', 'Gentle Monster x Maison Margiela MM108',
   'https://images.example.com/solutions/gm-mm108.jpg',
   '{"keywords": ["Gentle Monster", "Maison Margiela", "sunglasses", "collaboration"], "qa_pairs": [{"question": "What brand is this?", "answer": "Gentle Monster x Maison Margiela"}, {"question": "What is the product?", "answer": "MM108 collaborative sunglasses"}]}'::jsonb,
   'product', 'https://www.gentlemonster.com/example/mm108')
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- PRODUCTS (16 rows) — for enrich_node future use
-- ============================================================================
INSERT INTO products (id, name, brand, category, price, image_url, description, product_url, tags) VALUES
  ('prod-001', 'Classic Flap Bag',              'Chanel',          'bag',        11200000, 'https://images.example.com/products/chanel-flap.jpg',       'Chanel Classic Flap medium in black caviar leather',           'https://www.chanel.com/example/classic-flap',       '["Chanel", "bag", "classic"]'::jsonb),
  ('prod-002', 'Jackie 1961 Mini Shoulder Bag',  'Gucci',           'bag',         3200000, 'https://images.example.com/products/gucci-jackie.jpg',      'Gucci Jackie 1961 mini in beige GG canvas',                   'https://www.gucci.com/example/jackie',              '["Gucci", "bag", "Jackie"]'::jsonb),
  ('prod-003', 'Re-Edition 2005 Nylon Bag',      'Prada',           'bag',         2100000, 'https://images.example.com/products/prada-reedition.jpg',   'Prada Re-Edition 2005 nylon shoulder bag in black',            'https://www.prada.com/example/reedition',           '["Prada", "bag", "nylon"]'::jsonb),
  ('prod-004', 'Triomphe Shoulder Bag',          'Celine',          'bag',         4500000, 'https://images.example.com/products/celine-triomphe.jpg',   'Celine Triomphe shoulder bag in tan natural calfskin',         'https://www.celine.com/example/triomphe',           '["Celine", "bag", "Triomphe"]'::jsonb),
  ('prod-005', 'Lady Dior Mini Bag',             'Dior',            'bag',         6800000, 'https://images.example.com/products/dior-ladydior.jpg',     'Lady Dior mini bag in powder pink lambskin with gold hardware','https://www.dior.com/example/lady-dior',            '["Dior", "bag", "Lady Dior"]'::jsonb),
  ('prod-006', 'Wander Matelasse Bag',           'Miu Miu',        'bag',         3100000, 'https://images.example.com/products/miumiu-wander.jpg',     'Miu Miu Wander matelasse shoulder bag in pink',               'https://www.miumiu.com/example/wander',             '["Miu Miu", "bag", "Wander"]'::jsonb),
  ('prod-007', 'Loulou Small Chain Bag',         'Saint Laurent',   'bag',         3500000, 'https://images.example.com/products/ysl-loulou.jpg',       'Saint Laurent Loulou small chain bag in black leather',        'https://www.ysl.com/example/loulou',                '["Saint Laurent", "bag", "Loulou"]'::jsonb),
  ('prod-008', 'Leather Biker Jacket',           'Saint Laurent',   'jacket',      7200000, 'https://images.example.com/products/ysl-biker.jpg',        'Saint Laurent classic leather biker jacket',                   'https://www.ysl.com/example/biker',                 '["Saint Laurent", "jacket", "leather"]'::jsonb),
  ('prod-009', 'Tweed Jacket 2025 S/S',          'Chanel',          'jacket',      9800000, 'https://images.example.com/products/chanel-tweed.jpg',     'Chanel 2025 S/S tweed jacket in pink and white',              'https://www.chanel.com/example/tweed',              '["Chanel", "jacket", "tweed"]'::jsonb),
  ('prod-010', 'Crystal Mini Dress',             'Miu Miu',        'dress',       5600000, 'https://images.example.com/products/miumiu-crystal.jpg',   'Miu Miu crystal-embellished mini dress',                      'https://www.miumiu.com/example/crystal',            '["Miu Miu", "dress", "crystal"]'::jsonb),
  ('prod-011', 'Jentle Garden Sunglasses',       'Gentle Monster',  'sunglasses',   450000, 'https://images.example.com/products/gm-jentle.jpg',        'Gentle Monster x Jentle Garden oversized sunglasses',         'https://www.gentlemonster.com/example/jentle',      '["Gentle Monster", "sunglasses"]'::jsonb),
  ('prod-012', 'Oversized Logo Hoodie',          'Ader Error',      'hoodie',       380000, 'https://images.example.com/products/adererror-hoodie.jpg', 'Ader Error oversized logo hoodie in grey',                     'https://www.adererror.com/example/hoodie',          '["Ader Error", "hoodie", "oversized"]'::jsonb),
  ('prod-013', 'Padded Bomber Jacket',           'Ader Error',      'jacket',       520000, 'https://images.example.com/products/adererror-bomber.jpg', 'Ader Error padded bomber jacket in navy',                      'https://www.adererror.com/example/bomber',          '["Ader Error", "jacket", "bomber"]'::jsonb),
  ('prod-014', 'Deconstructed Blazer',           'Andersson Bell',  'jacket',       680000, 'https://images.example.com/products/andersson-blazer.jpg', 'Andersson Bell oversized deconstructed blazer',               'https://www.anderssonbell.com/example/blazer',      '["Andersson Bell", "blazer"]'::jsonb),
  ('prod-015', 'Cardigan Dress',                 'Thom Browne',     'dress',       4200000, 'https://images.example.com/products/thombrowne-dress.jpg', 'Thom Browne knit cardigan dress with grosgrain trim',         'https://www.thombrowne.com/example/cardigan-dress', '["Thom Browne", "dress", "knit"]'::jsonb),
  ('prod-016', 'Monolith Loafer',                'Prada',           'shoes',       1800000, 'https://images.example.com/products/prada-monolith.jpg',   'Prada Monolith brushed leather loafers',                      'https://www.prada.com/example/monolith',            '["Prada", "shoes", "loafer"]'::jsonb)
ON CONFLICT (id) DO NOTHING;
