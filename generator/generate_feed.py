#!/usr/bin/env python3
"""
Avito XML Feed Generator
========================
Generates Avito autoload XML feed from products.json + cities.json.

Usage:
    python generate_feed.py                          # Generate all feeds
    python generate_feed.py --product subnado-plus   # Generate specific product feed
    python generate_feed.py --validate               # Validate existing feeds

Output goes to feed/ directory.
"""

import json
import os
import sys
import argparse
from datetime import date
from xml.sax.saxutils import escape
import xml.etree.ElementTree as ET


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FEED_DIR = os.path.join(SCRIPT_DIR, '..', 'feed')

# Avito requires these fields for category "Спорт и отдых" > "Дайвинг и водный спорт"
REQUIRED_FIELDS = [
    'Category', 'GoodsType', 'WaterSportType', 'AdType',
    'Title', 'Description', 'Price', 'Condition', 'Images', 'Address'
]


def load_json(filename):
    path = os.path.join(SCRIPT_DIR, filename)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def escape_xml(text):
    """Escape special XML characters."""
    return escape(str(text))


def generate_ad_xml(product, city, today):
    """Generate XML for a single ad (product + city combination)."""
    ad_id = f"{product['id_prefix']}-{city['id']}"
    title = product['title_template'].format(city_suffix=city['suffix'])
    description = product['description_template'].format(city_suffix=city['suffix'])

    # Truncate title to 50 chars (Avito limit)
    if len(title) > 50:
        title = title[:47] + '...'

    lines = []
    lines.append('  <Ad>')
    lines.append(f'    <Id>{escape_xml(ad_id)}</Id>')
    lines.append(f'    <DateBegin>{today}</DateBegin>')
    lines.append(f'    <AllowEmail>Нет</AllowEmail>')
    lines.append(f'    <ManagerName>{escape_xml(product["manager"])}</ManagerName>')
    lines.append(f'    <ContactPhone>{escape_xml(product["phone"])}</ContactPhone>')
    lines.append(f'    <Category>{escape_xml(product["category"])}</Category>')
    lines.append(f'    <GoodsType>{escape_xml(product["goods_type"])}</GoodsType>')
    lines.append(f'    <WaterSportType>{escape_xml(product["water_sport_type"])}</WaterSportType>')
    lines.append(f'    <AdType>{escape_xml(product["ad_type"])}</AdType>')
    lines.append(f'    <Title>{escape_xml(title)}</Title>')
    lines.append(f'    <Description>{escape_xml(description)}</Description>')
    lines.append(f'    <Price>{product["price"]}</Price>')
    lines.append(f'    <Condition>{escape_xml(product["condition"])}</Condition>')

    # Images (Avito supports up to 10)
    lines.append('    <Images>')
    for img_url in product.get('images', [])[:10]:
        lines.append(f'      <Image url="{escape_xml(img_url)}"/>')
    lines.append('    </Images>')

    # Video URL (optional, YouTube link)
    if product.get('video_url'):
        lines.append(f'    <VideoURL>{escape_xml(product["video_url"])}</VideoURL>')

    lines.append(f'    <Address>{escape_xml(city["name"])}</Address>')
    lines.append(f'    <Availability>{escape_xml(product["availability"])}</Availability>')
    lines.append('  </Ad>')

    return '\n'.join(lines)


def generate_feed(product, cities, today):
    """Generate complete XML feed for a product across all cities."""
    parts = []
    parts.append('<?xml version="1.0" encoding="UTF-8"?>')
    parts.append('<Ads formatVersion="3" target="Avito.ru">')

    for city in cities:
        parts.append(generate_ad_xml(product, city, today))

    parts.append('</Ads>')
    return '\n'.join(parts) + '\n'


def validate_feed(filepath):
    """Validate an Avito XML feed file."""
    errors = []

    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
    except ET.ParseError as e:
        return [f"XML parse error: {e}"]

    if root.tag != 'Ads':
        errors.append(f"Root element should be 'Ads', got '{root.tag}'")

    if root.get('formatVersion') != '3':
        errors.append(f"formatVersion should be '3', got '{root.get('formatVersion')}'")

    ads = root.findall('Ad')
    if not ads:
        errors.append("No <Ad> elements found")

    for i, ad in enumerate(ads):
        ad_id = ad.find('Id')
        ad_label = ad_id.text if ad_id is not None else f"Ad #{i+1}"

        # Check required fields
        for field in REQUIRED_FIELDS:
            el = ad.find(field)
            if el is None:
                errors.append(f"[{ad_label}] Missing required field: {field}")
            elif field != 'Images' and (el.text is None or el.text.strip() == ''):
                errors.append(f"[{ad_label}] Empty required field: {field}")

        # Validate GoodsType value
        goods_type = ad.find('GoodsType')
        if goods_type is not None and goods_type.text:
            valid_goods = ['Дайвинг и водный спорт']
            if goods_type.text not in valid_goods:
                errors.append(f"[{ad_label}] Invalid GoodsType: '{goods_type.text}'. Must be one of: {valid_goods}")

        # Validate WaterSportType
        wst = ad.find('WaterSportType')
        if wst is not None and wst.text:
            valid_wst = ['Аксессуары для плавания']
            if wst.text not in valid_wst:
                errors.append(f"[{ad_label}] Invalid WaterSportType: '{wst.text}'. Must be one of: {valid_wst}")

        # Check images
        images = ad.find('Images')
        if images is not None:
            img_elements = images.findall('Image')
            if len(img_elements) == 0:
                errors.append(f"[{ad_label}] No images found inside <Images>")
            elif len(img_elements) > 10:
                errors.append(f"[{ad_label}] Too many images ({len(img_elements)}), max 10")
            for img in img_elements:
                url = img.get('url', '')
                if not url.startswith('http'):
                    errors.append(f"[{ad_label}] Invalid image URL: '{url}'")

        # Check title length (Avito max 50 chars)
        title = ad.find('Title')
        if title is not None and title.text and len(title.text) > 50:
            errors.append(f"[{ad_label}] Title too long ({len(title.text)} chars, max 50): '{title.text[:60]}...'")

        # Check price
        price = ad.find('Price')
        if price is not None and price.text:
            try:
                p = int(price.text)
                if p <= 0:
                    errors.append(f"[{ad_label}] Price must be positive, got {p}")
            except ValueError:
                errors.append(f"[{ad_label}] Invalid price: '{price.text}'")

    return errors


def main():
    parser = argparse.ArgumentParser(description='Avito XML Feed Generator')
    parser.add_argument('--product', help='Generate feed for specific product slug')
    parser.add_argument('--validate', action='store_true', help='Validate existing feeds')
    parser.add_argument('--date', help='Override date (YYYY-MM-DD format)')
    args = parser.parse_args()

    today = args.date or date.today().isoformat()

    if args.validate:
        # Validate all feeds in feed/ directory
        feed_dir = FEED_DIR
        if not os.path.isdir(feed_dir):
            print(f"Feed directory not found: {feed_dir}")
            sys.exit(1)

        all_ok = True
        for filename in sorted(os.listdir(feed_dir)):
            if filename.endswith('.xml'):
                filepath = os.path.join(feed_dir, filename)
                print(f"\n🔍 Validating {filename}...")
                errors = validate_feed(filepath)
                if errors:
                    all_ok = False
                    for err in errors:
                        print(f"  ❌ {err}")
                else:
                    print(f"  ✅ Valid! No errors found.")

        if all_ok:
            print("\n✅ All feeds are valid!")
            sys.exit(0)
        else:
            print("\n❌ Some feeds have errors!")
            sys.exit(1)

    # Generate feeds
    products = load_json('products.json')
    cities = load_json('cities.json')

    os.makedirs(FEED_DIR, exist_ok=True)

    for product in products:
        if args.product and product['slug'] != args.product:
            continue

        filename = f"avito_{product['slug'].replace('-', '_')}.xml"
        filepath = os.path.join(FEED_DIR, filename)

        xml_content = generate_feed(product, cities, today)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(xml_content)

        print(f"✅ Generated {filename} ({len(cities)} ads)")

        # Auto-validate
        errors = validate_feed(filepath)
        if errors:
            print(f"  ⚠️  Validation warnings:")
            for err in errors:
                print(f"    - {err}")
        else:
            print(f"  ✅ Validation passed!")


if __name__ == '__main__':
    main()
