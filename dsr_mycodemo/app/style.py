"""The app's one CSS block (Preview boxes, Welcome stage flow, soft accents); flow.init() loads it on every page.
Theme colours live in .streamlit/config.toml."""

CSS = """
<style>
:root {--clay: #D9A58B; --sand: #E9DFC7; --mist: #BFD8D2;}
.mc-preview {border: 2px dashed #9aa0a6; border-radius: 8px; padding: 0.7rem 1rem; margin: 0.6rem 0;
  background: rgba(150,150,150,0.12); color: #8a8f94; filter: grayscale(1);}
.mc-preview b {color: #8a8f94;}
.mc-tag {display: inline-block; border: 1px solid #9aa0a6; border-radius: 4px; padding: 0 6px;
  font-size: 0.75rem; letter-spacing: 0.05em; margin-right: 8px; color: #8a8f94;}
.sf-box {border: 2px solid #4F7F52; border-radius: 10px; padding: 0.55rem 1rem; text-align: center;
  font-weight: 600; background: rgba(79,127,82,0.15);}
.sf-box.off {border-color: #9aa0a6; background: rgba(150,150,150,0.12); color: #8a8f94;}
.sf-arrow {text-align: center; font-size: 1.3rem; line-height: 1.6rem; color: #8a8f94;}
div[data-testid="stMetric"] {background: var(--sand); border: 1px solid var(--clay); border-radius: 8px;
  padding: 0.5rem 0.8rem;}
.mc-step {color: #4F7F52; font-size: 0.85rem; font-weight: 600; margin-bottom: -0.8rem;}
</style>
"""
