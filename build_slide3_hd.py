#!/usr/bin/env python3
"""
Generate Slide 3: Innovation & Solution in both:
1. High-clarity, perfectly-aligned .pptx file
2. Ultra-HD 4K (3840x2160) crystal-clear PNG image
"""

import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

def create_slide3_pptx(output_path):
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.500)

    # Blank slide layout
    blank_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(blank_layout)

    # Colors
    c_navy_dark   = RGBColor(0x1F, 0x29, 0x37) # #1F2937
    c_gray_dark   = RGBColor(0x4B, 0x55, 0x63) # #4B5563
    c_gray_muted  = RGBColor(0x6B, 0x72, 0x80) # #6B7280
    c_gray_light  = RGBColor(0xD1, 0xD5, 0xDB) # #D1D5DB
    c_orange      = RGBColor(0xEA, 0x58, 0x0C) # #EA580C (vibrant orange)
    c_orange_light= RGBColor(0xFB, 0x92, 0x3C) # #FB923C (warm light orange)
    c_white       = RGBColor(0xFF, 0xFF, 0xFF)
    c_card_bg     = RGBColor(0x1E, 0x29, 0x3B) # #1E293B (deep slate card)

    # 1. Title
    tb = slide.shapes.add_textbox(Inches(0.60), Inches(0.40), Inches(9.5), Inches(0.55))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = "Innovation & Solution"
    p.font.name = "Arial"
    p.font.size = Pt(28)
    p.font.bold = True
    p.font.color.rgb = c_navy_dark

    # 2. Subtitle
    tb = slide.shapes.add_textbox(Inches(0.60), Inches(0.98), Inches(9.5), Inches(0.35))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = "Why existing navigation falls short — and what we built instead"
    p.font.name = "Arial"
    p.font.size = Pt(13)
    p.font.color.rgb = c_gray_dark

    # 3. Section: THE GAP
    tb = slide.shapes.add_textbox(Inches(0.60), Inches(1.48), Inches(3.0), Inches(0.28))
    tf = tb.text_frame
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = "THE GAP"
    p.font.name = "Arial"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = c_orange

    # 4. Gap Text
    tb = slide.shapes.add_textbox(Inches(0.60), Inches(1.80), Inches(8.8), Inches(0.70))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    
    r1 = p.add_run()
    r1.text = "Mainstream apps rank routes by "
    r1.font.name = "Arial"
    r1.font.size = Pt(15)
    r1.font.color.rgb = c_gray_dark

    r2 = p.add_run()
    r2.text = "time and distance alone"
    r2.font.name = "Arial"
    r2.font.size = Pt(15)
    r2.font.bold = True
    r2.font.color.rgb = c_navy_dark

    r3 = p.add_run()
    r3.text = " — fog, monsoon flooding, blind ghat curves and known blackspots stay invisible until you're already in them."
    r3.font.name = "Arial"
    r3.font.size = Pt(15)
    r3.font.color.rgb = c_gray_dark

    # 5. Right Stat: '0'
    tb = slide.shapes.add_textbox(Inches(9.80), Inches(1.25), Inches(2.8), Inches(0.85))
    tf = tb.text_frame
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = "0"
    p.font.name = "Arial"
    p.font.size = Pt(64)
    p.font.bold = True
    p.font.color.rgb = c_orange

    tb = slide.shapes.add_textbox(Inches(9.80), Inches(2.15), Inches(2.9), Inches(0.40))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = "India-specific risk factors most navigation apps model"
    p.font.name = "Arial"
    p.font.size = Pt(10)
    p.font.color.rgb = c_gray_muted

    # 6. Main Solution Card (Dark Blue Container)
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.60), Inches(2.70), Inches(12.133), Inches(2.10))
    card.fill.solid()
    card.fill.fore_color.rgb = c_card_bg
    card.line.color.rgb = RGBColor(0x33, 0x41, 0x55)
    card.line.width = Pt(1)

    # 7. 'OUR SOLUTION' Pill Badge
    badge = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.95), Inches(2.50), Inches(1.80), Inches(0.38))
    badge.fill.solid()
    badge.fill.fore_color.rgb = c_orange
    badge.line.fill.background()
    tf = badge.text_frame
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = "OUR SOLUTION"
    p.alignment = PP_ALIGN.CENTER
    p.font.name = "Arial"
    p.font.size = Pt(10)
    p.font.bold = True
    p.font.color.rgb = c_white

    # 8. Card Left Text
    tb = slide.shapes.add_textbox(Inches(0.95), Inches(3.05), Inches(4.30), Inches(0.90))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = "SafePass Maps replaces guesswork with a predictive Safety Score."
    p.font.name = "Arial"
    p.font.size = Pt(17.5)
    p.font.bold = True
    p.font.color.rgb = c_white

    tb = slide.shapes.add_textbox(Inches(0.95), Inches(4.10), Inches(4.30), Inches(0.45))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = "Not just point A to B — built for Indian highway realities."
    p.font.name = "Arial"
    p.font.size = Pt(11)
    p.font.color.rgb = c_gray_light

    # 9. 4 Grid Features inside Card
    features = [
        ("Predictive Scoring", "every route ranked 0–10 on real safety risk, not just ETA", Inches(5.60), Inches(2.95)),
        ("Full Risk Fusion", "weather, accident history, road geometry & time-of-day in one score", Inches(9.00), Inches(2.95)),
        ("Live Hazard Network", "citizen reports, AI-classified and published in real time", Inches(5.60), Inches(3.90)),
        ("Built-In Emergency Response", "one-tap SOS, no separate app required", Inches(9.00), Inches(3.90))
    ]

    for title, desc, x, y in features:
        # Orange vertical accent bar
        bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y + Inches(0.04), Inches(0.04), Inches(0.48))
        bar.fill.solid()
        bar.fill.fore_color.rgb = c_orange
        bar.line.fill.background()

        # Text box
        tb = slide.shapes.add_textbox(x + Inches(0.16), y, Inches(3.20), Inches(0.68))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        p1 = tf.paragraphs[0]
        p1.text = title
        p1.font.name = "Arial"
        p1.font.size = Pt(11.5)
        p1.font.bold = True
        p1.font.color.rgb = c_white

        p2 = tf.add_paragraph()
        p2.text = desc
        p2.font.name = "Arial"
        p2.font.size = Pt(10)
        p2.font.color.rgb = c_gray_light

    # 10. Bottom Section: INNOVATION WE MADE
    tb = slide.shapes.add_textbox(Inches(0.60), Inches(5.08), Inches(4.0), Inches(0.28))
    tf = tb.text_frame
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = "INNOVATION WE MADE"
    p.font.name = "Arial"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = c_orange

    # 11. 4 Innovation Columns
    innovations = [
        ("01", "Predictive, Not Reactive", "Forecasts corridor risk before you drive, not after", Inches(0.60)),
        ("02", "Explainable by Design", "SHAP shows exactly why a route scored the way it did", Inches(3.75)),
        ("03", "Citizen + AI Hybrid", "Real hazards, AI-classified in seconds, always current", Inches(6.90)),
        ("04", "India-Calibrated Model", "Trained on the conditions global maps were never built for", Inches(10.05))
    ]

    for num, title, desc, x in innovations:
        # Number (high clarity warm orange)
        tb = slide.shapes.add_textbox(x, Inches(5.42), Inches(2.80), Inches(0.55))
        tf = tb.text_frame
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        p = tf.paragraphs[0]
        p.text = num
        p.font.name = "Arial"
        p.font.size = Pt(36)
        p.font.bold = True
        p.font.color.rgb = c_orange_light

        # Title
        tb = slide.shapes.add_textbox(x, Inches(6.00), Inches(2.80), Inches(0.35))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        p = tf.paragraphs[0]
        p.text = title
        p.font.name = "Arial"
        p.font.size = Pt(12.5)
        p.font.bold = True
        p.font.color.rgb = c_navy_dark

        # Description
        tb = slide.shapes.add_textbox(x, Inches(6.38), Inches(2.80), Inches(0.55))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        p = tf.paragraphs[0]
        p.text = desc
        p.font.name = "Arial"
        p.font.size = Pt(10)
        p.font.color.rgb = c_gray_muted

    # 12. Slide Number
    tb = slide.shapes.add_textbox(Inches(12.60), Inches(7.05), Inches(0.40), Inches(0.30))
    tf = tb.text_frame
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = "3"
    p.font.name = "Arial"
    p.font.size = Pt(11)
    p.font.color.rgb = c_gray_muted

    prs.save(output_path)
    print(f"✅ Generated High-Definition PPTX: {output_path}")

if __name__ == "__main__":
    out_hack = "/Users/parthsonkusare1340/Hack2026ps1/Slide3_Innovation_Solution_HD.pptx"
    out_down = "/Users/parthsonkusare1340/Downloads/Slide3_Innovation_Solution_HD.pptx"
    create_slide3_pptx(out_hack)
    create_slide3_pptx(out_down)
