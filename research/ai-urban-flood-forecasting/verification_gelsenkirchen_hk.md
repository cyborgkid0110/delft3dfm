# Verification: Gelsenkirchen (C501–C526, S07) and Hong Kong (C601–C619, S08/S09)

Method: I read each original at the cited PDF page index with `pdftotext -layout`. I rendered and viewed the figure pages of S07 (p.9 Fig.1, p.11 Fig.2, p.12 Fig.3 zoomed, p.15 Fig.4, p.17 Fig.6 zoomed, p.22 Fig.8) and all four HK pages, because the HK text layer drops several phrases. For each NEG claim I keyword-searched the whole document.
Note: S07 has 26 PDF pages; the printed page numbers differ (PDF p.N = printed p.N−3 from p.7 on). All locators below are PDF page indices.

## Gelsenkirchen — S07 (Gelsenkirchen_Germany_KIWaSuS.pdf)

| Claim | Source / locator checked | Verdict | What the source actually says (short paraphrase) | Action |
|---|---|---|---|---|
| C501 | S07 p.1, p.4 (cover tables) | OK | Sub-project "GE-warnt" within the joint project KIWaSuS; funder BMBF; FKZ 13N15560; recipient Abwassergesellschaft Gelsenkirchen mbH; duration 01.04.2021–31.03.2024. | — |
| C502 | S07 p.8 §2.2 (partner table); p.9 Fig.1 | OK | Partners: HRW, GW AG, AGG, UDE, fuseki GmbH (formerly neusta sd west). Associated partners: Feuerwehr GE, LANUV, EG/LV, LAMBRECHT meteo, Provinzial. HRW's coordinating role ("Verbundkoordination Hochschule Ruhr West") appears only in Fig.1 on p.9. | Add p.9 Fig.1 to the locator for "điều phối". |
| C503 | S07 p.10 §3.1; Fig.2 on p.11 | OK | "Kanaleinzugsgebiet 3.219" (p.10); Fig.2 caption "Untersuchungsgebiet Gelsenkirchen-Ückendorf" (p.11). | Locator: Fig.2 is on p.11, not p.10. |
| C504 | S07 p.24 §5 | OK | System built "für einen Teilbereich des Stadtgebietes"; a city-wide system needs forecast models extended to the whole city and the sensor network expanded. | — |
| C505 | S07 p.21 §3.3.3; p.13 §3.3.1.1 | OK | Joint session on the "Demonstrator"/test data in Jan 2024 (p.13). Evaluation by simulating a past event, tried out by sewer operations and fire brigade via the expert app and WMS (p.21). The Fig.6 screenshot is titled "Demo KIWaSuS". | — |
| C506 | S07 p.22 §4.1; whole document searched (€, EUR, Euro) | OK | §4.1 says only that most of the budget went to AGG staff costs and that not all funds were drawn. No amounts anywhere. | — |
| C507 | S07 p.11–12 §3.1 | OK | AGG supplied Starkregengefahrenkarte, Kanalnetzdaten, Landnutzungsdaten and DGM. These were the basis for AP2 (Kanalnetzmodell) and AP6 (Oberflächenabflussmodell). | — |
| C508 | S07 p.11 §3.1 | OK | Measuring equipment installed in public sewers. MID sites chosen from structure drawings and deposition records. Rain-gauge sites chosen per DWD requirements. These extra requirements do not apply to the low-cost measuring equipment. | — |
| C509 | S07 whole doc (km, Länge, Schacht, Pump, Fläche, ha, Einwohner) + Figs 2, 5 | OK | No sewer length, manhole or pump count, or area. Manholes appear only as map layers or future query attributes (p.16). | — |
| C510 | S07 p.7 §2.1 (also p.2) | OK | Aim: a real-time warning and management system for urban flash floods using AI methods, "insbesondere maschinellen Lernverfahren". | — |
| C511 | S07 p.12 Fig.3 (rendered, zoomed) | OK | Fig.3: radar rain → Echtzeitkorrektur → Niederschlag (Prognosemodell) → Überstau (Prognosemodell) → Überflutungsflächen (Prognosemodell) → Visualisierung (Dashboard) / Bereitstellung (WMS-Raster). The rain forecast also feeds Überflutungsflächen directly. Ground gauges and flow classes go through Plausibilisierung/Korrektur into Überstau. | Optional: mention the plausibility-check branch. |
| C512 | S07 p.23 §4.3.1 | OK | Real-time forecast "für die nahe Zukunft (0,5-2 Stunden)". | — |
| C513 | S07 p.20 §3.3.2; p.26 (end of §5); also p.18 | OK | Warnstufe 1 is triggered "etwa 60 Minuten vor Beginn des Niederschlagsereignisses" (p.20). "Vorwarnzeit von ca. 60 Minuten" (p.26). | — |
| C514 | S07 p.17 Fig.6 + text (rendered, zoomed) | OK | Text: forecasts shown in "5-Minutenintervallen". The Fig.6 layer list shows ueberflutung_10_minuten … ueberflutung_60_minuten in 5-min steps (the list may scroll below 10). | — |
| C515 | S07 whole doc (neuronal, LSTM, CNN, Auflösung, Raster, Meter) + Figs 3, 5, 6 | OK | No ML architecture and no numerical spatial resolution. Only the qualitative "zeitlich und räumlich hochaufgelöst" (p.23). | — |
| C516 | S07 p.21 §3.3.3; Fig.8 p.22 (rendered) | OK | Simulation of one past event compared with fire-brigade call-outs and the sewer operator's experience: "guten Übereinstimmung". Three prominent spots shown "exemplarisch" (Fig.8). The qualitative classification is reasonable. | Nuance: the agreement is stated overall; the three spots are examples. |
| C517 | S07 p.21 §3.3.3 | OK | Hotspots of the static hazard map and the dynamic forecast are "nahezu deckungsgleich". | — |
| C518 | S07 p.16 §3.3.1.2 (also p.12 §3.2) | OK | "Modellgüte der Prognose" is in the list of future functions. Users find easily visible quality info "wünschenswert" (p.12). | — |
| C519 | S07 whole doc (Kalibr, Validier, Genauigkeit, Güte, RMSE, NSE) | PARTIAL | No quantitative metrics and no calibration are reported. A qualitative evaluation/validation against fire-brigade call-outs is reported in §3.3.3 (p.21–22), so "không có validation" overstates. | Reword: "Không có chỉ số định lượng, không có calibration; chỉ có đánh giá định tính bằng so sánh với điểm can thiệp cứu hỏa (p.21–22, xem C516)". |
| C520 | S07 p.12 Fig.3; p.11 | OK | Fig.3 data capture: Niederschlag (Radarmessungen), Niederschlag (Bodenmessung), Durchflussklassen (Messungen im Kanal). MID and low-cost sensors on p.11. | — |
| C521 | S07 whole doc (Training, Szenario, synthetisch, Datensatz) | OK | Training data are not described anywhere. | — |
| C522 | S07 p.14–15 (§3.3.1.2, Fig.4), p.17 | OK | The data platform (hetida) feeds an expert app ("Expertensystem") and WMS. WMS is integrated into the city Geoportal (p.14, p.17) and the fire-brigade information system (p.14, p.17). | — |
| C523 | S07 p.19–20 Fig.7; p.20 text (rendered table p.19–20) | OK | DWD-based Vorwarnung plus Warnstufen 1–3. Warnstufe 2: at least one forecast hotspot exceeds 25 cm water depth. | Locator: text is on p.20; p.21 is not needed. |
| C524 | S07 p.18 §3.3.1.3 (p.19 context) | OK | A lead time of about 60 min works against precautionary measures. The fire brigade would need at least 6 h for evacuations (p.18). On p.19 the fire brigade says it cannot take precautionary measures. | — |
| C525 | S07 whole doc (Rechenzeit, Laufzeit, Fehlalarm) | OK | No run time. "Fehlalarm" appears only about DWD regional warnings (p.2, p.7), not as a system false-alarm rate. | — |
| C526 | S07 whole doc (GPU, Server, Hardware, Cloud, Python, TensorFlow) | OK | Not reported. p.24 says only that funding for sensors and IT support must be clarified within the municipality. | — |

## Hong Kong — S08 (DEVB(W)093), S09 (DEVB(W)094)

| Claim | Source / locator checked | Verdict | What the source actually says (short paraphrase) | Action |
|---|---|---|---|---|
| C601 | S08 p.1 (Reply) | OK | "systems that are being used or developed by the DSD include the AI Flood Monitoring System and the Smart Flood Forecast and Alert System". | — |
| C602 | S08 p.2 (rendered; the phrase is missing from the text layer) | OK | With South China University of Technology; "scheduled for trials in mid-2026 at 3 locations, including Lam Tsuen River in Tai Po, Wan Chai, and Tsui Ping River in Kwun Tong". | — |
| C603 | S08 p.2 | OK | "development cost is estimated at around $1.3 million, which covers the operational expenditure at the 3 trial locations in 2026-27". | Optional: note HK$. |
| C604 | S08 p.2 | OK | Developed in 2024 with HKUST. Piloted at Chatham Road South (TST), Tai Kiu Tsuen and Tung Tau Wai Village (Yuen Long). | — |
| C605 | S08 p.2 | OK | Expanded with HKPF; "now connected to over 300 CCTV cameras under the 'SmartView' initiative". | — |
| C606 | S08 p.2 | OK | Development cost about $6 million; annual operational expenditure about $1.4 million. | — |
| C607 | S08 p.2 | OK | M³ developed in-house in 2024; used for flood risk assessments since 2025; "no additional costs are involved" (internal staff). | Wording nuance: "no *additional* costs". |
| C608 | S09 p.2 | OK | "In 2025-26, the operational expenditure of the Hydrometric Information System and the Flood Monitoring Devices was about $4 million"; later years are expected to be similar. | — |
| C609 | S09 p.1 (rendered; the phrase is missing from the text layer) | PARTIAL | "comprises over 300 water level sensors and rain gauges, providing real-time monitoring of water levels in main rivers or drainage channels, as well as rainfall across various districts". The 300 is the combined total. Rain gauges measure rainfall across districts, not in rivers or channels. | Reword: "hơn 300 cảm biến mực nước và trạm đo mưa (tổng), giám sát mực nước sông chính/kênh thoát nước và lượng mưa các quận". |
| C610 | S09 p.2 | OK | Since 2024, smart sensors called "Flood Monitoring Devices" are installed along selected carriageways; more than 100 so far, monitoring real-time road water level. | — |
| C611 | S08, S09 whole (sewer, pipe, manhole, pump, km, tunnel, storage) | OK | No drainage-network inventory. Only "drainage channels" and "blocked drains". | — |
| C612 | S08 p.2 (and p.1 question) | OK | "by leveraging an AI large vision-language model"; road CCTV images used "to detect and analyse street flooding"; "instantly issues an alert". | — |
| C613 | S08 p.2 | OK | "integrates big data and advanced AI technologies". No architecture given. | — |
| C614 | S08 p.2 (same in S09 p.2) | OK | M³ is "a real-time territorial flood risk system" built "to break through the limitations of traditional hydraulic models that requiring a long time for computation". It is not itself called AI, although it is described under the "Smart Flood Forecast and Alert System" heading. | — |
| C615 | S08, S09 whole (accuracy, %, precision, recall, calibr, valid, verif) | OK | No accuracy metrics. | — |
| C616 | S08 p.2; S09 p.1–2 | OK | No training data described. Operational inputs: road CCTV images, water-level sensors and rain gauges, Flood Monitoring Devices. | — |
| C617 | S09 p.2 (last paragraph) | PARTIAL | "The DSD currently performs real-time monitoring …, flood forecast and monitors flooding … *separately* through the 3 aforementioned systems … In 2025, most flooding cases could be resolved within 1 to 2 hours." This is the DSD's overall case-resolution time. It is not attributed to the systems, the systems are run separately, and no baseline is given. "Kết quả vận hành tổng hợp của 3 hệ thống" overstates. | Reword: "Năm 2025 phần lớn các vụ ngập được xử lý trong 1–2 giờ (con số phản ứng tổng thể của DSD, nêu sau khi mô tả 3 hệ thống vận hành riêng rẽ; không quy kết nhân quả, không có baseline)" {S09: p.2}. |
| C618 | S08 p.2 (rendered; the phrase is missing from the text layer) | PARTIAL | "enabling forecasts of flood risks in coastal low-lying **or windy residential areas** ahead of Severe or Super Typhoons". The claim omits windy residential areas. | Add "hoặc khu dân cư lộng gió" {S08: p.2; also S09: p.2}. |
| C619 | S08, S09 whole (GPU, server, cloud, comput, hardware, software) | OK | No IT infrastructure reported. "computation" appears only in the M³ motivation. | — |

## Summary
Checked 45 of 45. OK 41, PARTIAL 4 (C519, C609, C617, C618), WRONG 0, NOT-FOUND 0, BAD-REF 0, OUT-OF-CONTEXT 0, STALE 0.
Locator hints for OK claims: C502 add p.9 Fig.1; C503 Fig.2 is on p.11; C523 text is on p.20.
