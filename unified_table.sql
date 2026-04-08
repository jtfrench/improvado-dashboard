-- ============================================================
-- Improvado Senior Marketing Analyst Assignment
-- Unified Cross-Channel Advertising Table
-- ============================================================

-- Step 1: Create the unified table
CREATE OR REPLACE TABLE unified_ads (
    -- Common dimensions
    date                    DATE,
    source_platform         VARCHAR(20),
    campaign_id             VARCHAR(50),
    campaign_name           VARCHAR(200),
    ad_group_id             VARCHAR(50),
    ad_group_name           VARCHAR(200),

    -- Common metrics (shared across all platforms)
    impressions             NUMBER,
    clicks                  NUMBER,
    spend                   FLOAT,
    conversions             NUMBER,

    -- Facebook-specific metrics
    video_views             NUMBER,          -- also on TikTok
    engagement_rate         FLOAT,
    reach                   NUMBER,
    frequency               FLOAT,

    -- Google Ads-specific metrics
    conversion_value        FLOAT,
    quality_score           NUMBER,
    search_impression_share FLOAT,

    -- TikTok-specific metrics (video funnel)
    video_watch_25          NUMBER,
    video_watch_50          NUMBER,
    video_watch_75          NUMBER,
    video_watch_100         NUMBER,

    -- TikTok-specific metrics (social engagement)
    likes                   NUMBER,
    shares                  NUMBER,
    comments                NUMBER
);

-- Step 2: Insert Facebook data
INSERT INTO unified_ads
SELECT
    date,
    'Facebook'              AS source_platform,
    campaign_id,
    campaign_name,
    ad_set_id               AS ad_group_id,
    ad_set_name             AS ad_group_name,
    impressions,
    clicks,
    spend,
    conversions,
    video_views,
    engagement_rate,
    reach,
    frequency,
    NULL                    AS conversion_value,
    NULL                    AS quality_score,
    NULL                    AS search_impression_share,
    NULL                    AS video_watch_25,
    NULL                    AS video_watch_50,
    NULL                    AS video_watch_75,
    NULL                    AS video_watch_100,
    NULL                    AS likes,
    NULL                    AS shares,
    NULL                    AS comments
FROM facebook_ads;

-- Step 3: Insert Google Ads data
INSERT INTO unified_ads
SELECT
    date,
    'Google Ads'            AS source_platform,
    campaign_id,
    campaign_name,
    ad_group_id,
    ad_group_name,
    impressions,
    clicks,
    cost                    AS spend,
    conversions,
    NULL                    AS video_views,
    NULL                    AS engagement_rate,
    NULL                    AS reach,
    NULL                    AS frequency,
    conversion_value,
    quality_score,
    search_impression_share,
    NULL                    AS video_watch_25,
    NULL                    AS video_watch_50,
    NULL                    AS video_watch_75,
    NULL                    AS video_watch_100,
    NULL                    AS likes,
    NULL                    AS shares,
    NULL                    AS comments
FROM google_ads;

-- Step 4: Insert TikTok data
INSERT INTO unified_ads
SELECT
    date,
    'TikTok'                AS source_platform,
    campaign_id,
    campaign_name,
    adgroup_id              AS ad_group_id,
    adgroup_name            AS ad_group_name,
    impressions,
    clicks,
    cost                    AS spend,
    conversions,
    video_views,
    NULL                    AS engagement_rate,
    NULL                    AS reach,
    NULL                    AS frequency,
    NULL                    AS conversion_value,
    NULL                    AS quality_score,
    NULL                    AS search_impression_share,
    video_watch_25,
    video_watch_50,
    video_watch_75,
    video_watch_100,
    likes,
    shares,
    comments
FROM tiktok_ads;

-- Step 5: Verify row counts match expectations
-- Facebook: 110 rows, Google: 109 rows, TikTok: 109 rows = 328 total
SELECT source_platform, COUNT(*) AS row_count
FROM unified_ads
GROUP BY source_platform
ORDER BY source_platform;
