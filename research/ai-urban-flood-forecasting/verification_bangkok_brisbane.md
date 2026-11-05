# Verification: Bangkok (S02, C201–C225) and Brisbane (S03, C301–C320)

Method: for every claim, ran `pdftotext -layout` on the cited page and rendered the slide (pdftoppm, 60–250 dpi) and viewed it. For S02 p.13 I also extracted the embedded images (pdfimages) because two of the four plots are hidden under the visible ones. For the NEG claims I read the whole text of each deck (S02: 17 slides, S03: 43 slides) and viewed every slide.

## S02 – Bangkok (sources/Bangkok_Thailand_MottMacDonald-SIWW2022.pdf)

| Claim | Source / locator checked | Verdict | What the source actually says (short paraphrase) | Action |
|---|---|---|---|---|
| C201 | S02 p.1 | OK | "Delivering Smart Flood Management in Bangkok – Sharla McGavock, Mott MacDonald, Singapore International Water Week, 19 April 2022". | – |
| C202 | S02 p.2 | OK | "Bangkok Flood Management Decision Support System – A global first real-time stormwater flood forecasting system that can accurately predict where and when flooding will occur". | – |
| C203 | S02 p.5 | OK | Three bullets: targeted rainfall radar network improvements; ML to overcome the limitations of hydraulic models; integration of sensor data, rainfall and flooding predictions and alarming in Moata. | – |
| C204 | S02 p.15 (rendered) | OK | The Moata screenshot's layer list ends with "Pilot Area" (red outline on the map). No area or population is given anywhere in the deck. | – |
| C205 | S02 p.15 | OK | "Direct gauge feeds from BMA". | – |
| C206 | S02 p.5, p.9 (rendered) | OK | p.5 screenshot filter: "Oct 1, 2021 5:59 AM to Oct 3, 2021 5:59 AM". p.9: "Aug 27, 2021 3:17 PM to Aug 27, 2021 8:48 PM". | – |
| C207 | Whole deck (text and all slides) | PARTIAL | No area, population or cost. However, p.3 "Global Future Cities Programme – South East Asia" gives "13 projects, 9 cities, 6 countries, 3 years", and Bangkok is one of the cities. This is a duration at programme level, not for the Bangkok project. | Keep "no area/population/cost". Qualify the duration part: "chỉ có thời lượng chương trình Global Future Cities Programme SEA (3 năm, 13 dự án, 9 thành phố) {S02: p.3}; không có thời gian riêng của dự án Bangkok". |
| C208 | S02 p.11 | OK | "Physical environment (topography, land use, drainage network etc)". | – |
| C209 | S02 p.9 (rendered) | OK | Moata "Monitoring" layers: Rainfall Gauge, Road Flood Level Gauge, River/Canal Level Gauge, River/Canal Flow Gauge. | – |
| C210 | Whole deck | OK | No counts or lengths of sewers, manholes, pumps or canals. p.9 shows gauge icons only, with no counts. | – |
| C211 | S02 p.10, p.11 | BAD-REF | p.10: "Machine learning surrogate model … Based on calibrated hydraulic flood model". The name TUFLOW is not on p.10. It appears on p.11–12 ("Simulation software (TUFLOW)"). The content is correct. | Change the locator to {S02: p.10–11}. |
| C212 | S02 p.11–12 (rendered) | OK | p.11 chain: Rainfall → [physical environment + physical equations + TUFLOW] → Flood level (on a 2D grid). p.12 draws a "Machine learning" box around the environment, equations and TUFLOW block. | – |
| C213 | Whole deck | OK | No ML architecture, lead time or grid resolution. There is only "Outputs every 10 mins" (p.13). Plot titles say "Cell … of 740", but no resolution is given. | – |
| C214 | S02 p.13 | OK | "Relative error of 2cm", with no reference stated. The same slide plots "target" vs "pred", so the inference that the reference is the hydraulic model is reasonable, and [Không rõ] fits. | – |
| C215 | S02 p.10 | OK | "Based on calibrated hydraulic flood model". The deck gives no calibration metrics. | – |
| C216 | S02 p.8 (zoomed at 200 dpi) | OK | Box-plot medians as read: RADAR UNCORRECTEDD r²≈0.665, bias≈0.58. GAUGE r²≈0.77, bias≈1.01. RADAR r²≈0.81, bias≈0.98. The legend says only "RADAR". Reading it as "corrected radar" is reasonable given the "Continuous calibration" bullet. | Optional: note that the legend reads "RADAR" (not "corrected") and that the diamonds are means. |
| C217 | S02 p.13 (render + extracted images) | OK | Four target/pred/total-rainfall plots are embedded: Event 161016 (cell 873,326), 160625 (929,219), 161024 (454,239) and 171002 (99,514). Only 161024 and 171002 are visible in the rendered slide; the other two sit underneath them. "pred" closely tracks "target". | Optional: note that only 2 plots are visible on the slide. |
| C218 | Whole deck | OK | No NSE, RMSE or CSI, and no comparison against observed flooding. p.15 shows only a "Historical event – 24-25 Ma…" model-output layer. | – |
| C219 | S02 p.10–13 | OK | The inference follows: the ML is a "surrogate" "based on calibrated hydraulic flood model", and the ML "target" vs "pred" plots are per event. The source never states the training data explicitly. | – |
| C220 | Whole deck | OK | No number of scenarios, no design storms, no data split. There are only 4 event IDs in the plots and "…of 740", which is undefined. | – |
| C221 | S02 p.13 | OK | "Flood predictions in 1 second", "Outputs every 10 mins". | – |
| C222 | S02 p.16 | OK | Key outcomes: 1. Real-time flood insights, 2. Proactive flood response, 3. Opening opportunities. | – |
| C223 | S02 p.15 | OK | Direct gauge feeds from BMA; secure, private web portal; real-time flood forecasting maps and animations; flood warning alarms. | – |
| C224 | S02 p.10 (zoomed at 160 dpi) | PARTIAL | The two maps ("Machine learning model" / "Hydraulic model", colour bar 0–1.2+, no unit) have nearly the same spatial pattern. The ML map shows noticeably more and larger dark-blue (~0.5–0.8) patches than the hydraulic map, so "gần như giống nhau" overstates it a little. No numeric comparison is given. | Reword: "phân bố không gian rất tương tự; mô hình ML hiển thị một số ô sâu (~0,5–0,8) nhiều/lớn hơn; so sánh chỉ trực quan, thang màu không ghi đơn vị" {S02: p.10}. |
| C225 | Whole deck | OK | No hardware, training time or ML framework. Software named: TUFLOW (p.11–12) and Moata (p.5, 9, 14). | – |

## S03 – Brisbane (sources/Brisbane_Australia_FloodMapp-FIG2025.pdf)

| Claim | Source / locator checked | Verdict | What the source actually says (short paraphrase) | Action |
|---|---|---|---|---|
| C301 | S03 p.8, p.1 | BAD-REF | p.8 has the product part: "FloodMapp DASH – Live, operational impact intelligence; Purpose built for emergency management". p.8 does not mention FIG Working Week or Brisbane. That is on p.1: "Presented at the FIG Working Week 2025 in Brisbane, Australia, 6–10 April 2025", author Juliette Murphy. | Change the locator to {S03: p.1, p.8}. Optionally add the author (Juliette Murphy) and the dates 6–10/04/2025. |
| C302 | S03 p.8 | OK | "Scalable from property level to national scale". | – |
| C303 | S03 p.26 | OK | "State-wide Deployment – April, 2025 – Up to 1400 gauges", with a Queensland map. | – |
| C304 | S03 p.27 | OK | "Catchment Size – Stonehenge and Retreat gauges 139,000km²" (slide dated April 2025). | – |
| C305 | S03 pp.12–41 | OK | TC Alfred, ForeCast/NowCast, March 2025 (p.13). Sites (pp.17–23) include Kedron Brook–Widdop St Nundah, Enoggera Ck–Officeworks Wilston and Coorparoo, Brisbane, plus Laidley, Nambour, Obi Obi Ck and Coomera. Western QLD Floods: section title "April 2025" (p.25), with event slides dated March–April 2025 (pp.28–32). Transport for NSW (p.33). City of Norfolk (p.38) and Norfolk, VA (p.12, p.41). | – |
| C306 | Whole deck | OK | No project cost, duration, population or Brisbane urban area. p.2 shows national disaster-cost estimates (Deloitte 2021), not project cost. The only area figure is the 139,000 km² catchment. | – |
| C307 | S03 p.10 + whole deck | OK | p.10 diagram: Live Data Collection Service → ForeCast Meteorological Data → DASH Hydrologic Model; River Levels → DASH 2D Hydraulic Model → products every hour. Nothing on sewers, manholes or pumps anywhere. | – |
| C308 | S03 p.8 + whole deck | OK | "Enhances physical hydrology and hydraulics with AI and Machine learning". This is the only AI/ML mention in the deck, and no architecture is given. | – |
| C309 | S03 p.8, p.10 | OK | p.8: "Dynamic hourly updates … using live rainfall & flood sensor data". p.10: ForeCast meteorological data, river levels, "Every hour". | – |
| C310 | S03 p.8, p.5, p.10 | BAD-REF | p.8: "Flood extent, depth, and impacts delivered via API into any GIS system". The terms ForeCast/NowCast/PostCast are not on p.8. They appear on p.5 ("Intelligence – Before, During, After") and p.10 ("FloodMapp Products: NowCast, PostCast, ForeCast"). The content is correct. | Change the locator to {S03: p.8, p.5, p.10}. |
| C311 | S03 p.8 | OK | "10m - 1m resolution", "Property level accuracy". | – |
| C312 | S03 p.27 (zoomed at 250 dpi) | OK | The "Hydrology Admin" screenshot has radio options "Model quality earliest rated / 6H / 24H / 72H / Protected model". No lead time is stated anywhere. The inference is appropriately hedged. | Optional: also list "Model quality earliest rated". |
| C313 | S03 p.12 | OK | "Calibration & Validation": river gauge hydrographs, media imagery, drone videos, pre-existing flood studies, traffic camera imagery, social media photos/videos, high water marks, satellite imagery. The slide does not say which data are used for calibration and which for validation, so [Không rõ] is reasonable. | – |
| C314 | S03 p.29 | OK | "Thomson River ForeCast, Stonehenge, QLD March 2025": ForeCast peak 158.5 m, gauge datum 150.6, ForeCast height 7.9 m, Observed Peak 7.4 m (forecast issued 2025-03-23 00:00). 0.5/7.4 = 6.8%, which rounds to about 7%. | – |
| C315 | S03 pp.17–23, 30–32 | OK | Side-by-side photos and model maps for the TC Alfred sites (pp.17–23) and for Jundah, Thargomindah and Birdsville (pp.30–32). The comparison is qualitative. | – |
| C316 | Whole deck | OK | No NSE, RMSE or CSI. The only quantitative comparison is the single peak at p.29. | – |
| C317 | S03 p.7, p.15 | OK | p.7 "The Power of Big Data" shows images only: a BoM gauge hydrograph, a Western Australia floodplain-mapping viewer, satellite imagery, an aerial/drone photo, a depth staff gauge and a sensor station. p.15 "Situational Intel. Crowdsourced data." shows the NowCast map with Logan flood-camera popups. No training dataset is described. | Minor: what the draft calls "camera" on p.7 is an aerial/drone photo, and the p.7 list could add the floodplain-mapping image. |
| C318 | S03 p.11 | OK | "Delivery via API as WMS/WFS or Esri REST Services"; "24/7 accessibility with 99.5% uptime". The slide shows logos for waze, QGIS, esri, HERE, JUVARE, WebEOC and genasys, with no explicit "integrated with" wording. | Optional: add HERE, Juvare and Genasys, or describe these as logos of compatible platforms. |
| C319 | S03 p.16, pp.34–41 | OK | p.16 "State Disaster Coordination Centre" (photos, inside the TC Alfred section). Transport for NSW: impact dashboards (pp.34–37; p.36 "NSW Vulnerable Transport Assets in Severe Weather Event – Oct 2022"). Norfolk: "Roadway Intelligence" and "Live Road Closures & Re-Routing" (pp.39–41, Waze/Google-maps style). | Optional: note that the NSW dashboard example dates from Oct 2022, and that "Queensland" comes from context (the p.16 slide text doesn't name it). |
| C320 | S03 p.10, p.27 + whole deck | OK | p.10: GeoServer, FloodMapp ArcGIS Enterprise, FloodMapp Esri cloud services, client ArcGIS Online/Enterprise. p.27: admin menu (DB, Reports, Rollout, Forecast, Interpolation, Build Model, Animation). No training hardware or infrastructure anywhere. | – |

## Summary

Checked 45 of 45 (S02: 25, S03: 20).
- OK: 40
- PARTIAL: 2 (C207, C224)
- BAD-REF: 3 (C211, C301, C310); in all three the content is correct and only the locator needs extending.
- WRONG / NOT-FOUND / OUT-OF-CONTEXT / STALE: 0
