"""The app's one CSS block (Preview boxes, Welcome stage flow, soft accents); flow.init() loads it on every page.
Theme colours live in .streamlit/config.toml."""

CSS = """
<style>
:root {--pink: #E2C6BE; --mauve: #93746A; --moss: #5E6B3A;}
.mc-preview {border: 2px dashed #9aa0a6; border-radius: 8px; padding: 0.7rem 1rem; margin: 0.6rem 0;
  background: rgba(150,150,150,0.12); color: #8a8f94; filter: grayscale(1);}
.mc-preview b {color: #8a8f94;}
.mc-tag {display: inline-block; border: 1px solid #9aa0a6; border-radius: 4px; padding: 0 6px;
  font-size: 0.75rem; letter-spacing: 0.05em; margin-right: 8px; color: #8a8f94;}
.sf-box {border: 2px solid #8A5A3B; border-radius: 10px; padding: 0.55rem 1rem; text-align: center;
  font-weight: 600; background: rgba(138,90,59,0.12);}
.sf-box.off {border-color: #9aa0a6; background: rgba(150,150,150,0.12); color: #8a8f94;}
.sf-arrow {text-align: center; font-size: 1.3rem; line-height: 1.6rem; color: #8a8f94;}
div[data-testid="stMetric"] {background: var(--pink); border: 1px solid var(--mauve); border-radius: 8px;
  padding: 0.5rem 0.8rem;}
.mc-step {color: var(--moss); font-size: 0.85rem; font-weight: 600; margin-bottom: -0.8rem;}
</style>
"""
