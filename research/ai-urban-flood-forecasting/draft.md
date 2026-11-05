# DRAFT — Tổng hợp các dự án dự báo ngập lụt đô thị bằng AI (bản nháp có claim ID)

> Bản nháp làm việc (stage 2). Mỗi câu có claim ID và locator `{Sxx: trang, mục, bảng/hình}`. Trang = trang PDF (số trang in ghi trong notes). `[INF]` = suy luận của người tổng hợp.

## Giới thiệu (placeholder)
9 tài liệu, 6 dự án/hệ thống: Aachen (ISRV), Bangkok (Mott MacDonald), Brisbane/Queensland (FloodMapp DASH), Dorsten (PuwaSTAR), Gelsenkirchen (KIWaSuS/GE-warnt), Hong Kong (DSD).

---

## 1. Aachen, Đức — dự án ISRV (S01)

### I1 Phạm vi, quy mô
- [C101] Mục tiêu: phát triển hệ thống cảnh báo sớm ngập do mưa lớn dựa trên AI, kết hợp hệ thống thông tin giao thông thời gian thực {S01: p.7, §1.1}.
- [C102] Tài trợ bởi chương trình mFUND của Bộ Số hóa và Giao thông Đức (BMDV), kinh phí 439.630 € {S01: p.8, §1.2}.
- [C103] Thời gian dự án 01.11.2021–31.10.2024 (36 tháng) {S01: p.8, §1.2}.
- [C104] Đối tác: RWTH Aachen IWW (điều phối), KISTERS AG, SCHWIETERING-BUNG Ingenieure, 4traffic SET; hợp tác thêm với TP Aachen, ASEAG, Regionetz {S01: p.7–8 §1.1; p.17 §1.5}.
- [C105] Vùng mô phỏng thủy động lực là khu vực TP Aachen với diện tích 61 km² {S01: p.12, Table 1, AP1}.
- [C106] Hai điểm nóng trọng tâm: hầm chui Westbahnhof và Kaiserplatz (8 hộp cảm biến giao thông lắp tại Kaiserplatz) {S01: p.33 §2.1.3 e); p.19 §2.1.1}.
- [C107] Mức độ triển khai: demonstrator/nguyên mẫu; hệ thống phản hồi giao thông vẫn ở "Prototypstadium" {S01: p.20 §2.1.1 AP4; p.17 §1.4.2}.
- [C108] Dữ liệu cảm biến giao thông 4traffic không được tích hợp vận hành do chậm lắp đặt và sự cố nguồn điện {S01: p.14 Table 1 AP4; p.19 §2.1.1; p.27 §2.1.3 b)}.
- [C109] Đang xây dựng ("in Arbeit") quan hệ đối tác với FloodWaive Predictive Intelligence GmbH — đơn vị phát triển tiếp mô hình DL của RWTH và thương mại hóa dưới tên "AI-FloodCast" {S01: p.50, §2.5}.

### I2 Hạ tầng thoát nước
- [C110] Mô hình 2D MIKE+/MIKE FM (phương trình nước nông), lưới phi cấu trúc thích ứng 4 m² (đô thị) đến 9 m² (ngoài đô thị); nhà được tích hợp vào DTM {S01: p.12 Table 1 AP1; p.26–27 §2.1.3 a)}.
- [C111] Mạng cống chỉ được biểu diễn đơn giản dưới dạng nguồn/điểm thu (source/sink) hoặc khấu trừ mưa theo diện tích, không có mô hình cống 1D tường minh {S01: p.26, §2.1.3 a)}.
- [C112] Báo cáo thừa nhận việc không mô hình hóa mạng cống gây bất định cho dự báo {S01: p.47, §2.2}.
- [C113] Không có số liệu chiều dài cống, hố ga, trạm bơm, hồ điều hòa (NEG) {S01: toàn văn, NEG}.

### I3 Mô hình AI
- [C114] Mô hình dự báo ngập "floodGAN": GAN, generator U-Net (encoder–decoder), discriminator PatchGAN, hàm mất mát adversarial + L1 {S01: p.28, §2.1.3 c); p.13, Table 1 AP3}.
- [C115] Đầu vào: dự báo mưa nowcast từ radar băng X của KISTERS; đầu ra: bản đồ độ sâu ngập 2 m, bước 5 phút, chân trời 1 h 55 min, xuất file TIF {S01: p.29, §2.1.3 c) "Modellintegration"}.
- [C116] Nowcast mưa (pySTEPS, optical flow phương pháp VET) có độ phân giải 125 m, bước 5 phút, dự báo 2 h, cập nhật 10 phút/lần {S01: p.22–23 Table 2–3}.
- [C117] Thời gian cảnh báo hiệu quả khoảng 30 phút (giới hạn bởi kỹ năng nowcast mưa) {S01: p.24, §2.1.3 a) "Analyse"}.
- [C118] Mô hình chỉ được huấn luyện cho kịch bản mưa 1 giờ {S01: p.47, §2.2}.
- [C119] Mô hình sinh mưa "synRainGAN": GAN sinh trường mưa 32×32, tối ưu Adam, learning rate 0,0002 {S01: p.25–26, §2.1.3 a)}.

### I4 Chỉ số đánh giá
- [C120] [Validation mô hình thủy lực — định tính; tài liệu không mô tả calibration] MIKE+ được kiểm chứng định tính bằng hình ảnh trận ngập thực 29.05.2018, "mức độ phù hợp cao", không có chỉ số định lượng {S01: p.27, §2.1.3 a)}.
- [C121] [Validation AI — định tính] "Kiểm tra validation sâu rộng" trên sự kiện mưa tổng hợp và sự kiện lịch sử ở Aachen được cho là khẳng định hiệu quả cao và tính thực tiễn của mô hình DL; riêng biệt, báo cáo nêu mô hình tăng tốc lớn so với mô hình thủy động lực "không mất độ chính xác đáng kể" — cả hai đều không có giá trị số {S01: p.28, §2.1.3 c)}.
- [C122] [Verification AI – định tính] Trận mưa thực 02.05.2024: vùng ngập dự báo tại Westbahnhof khớp quan sát cả về không gian và mực nước; không có chỉ số {S01: p.30–31, Fig. 7}.
- [C123] [Đánh giá đầu vào, không phải AI] FSS của nowcast mưa trên 10 sự kiện 2022–2023, ngưỡng tham chiếu FSS = 0,543; kỹ năng hữu ích 15–40 phút ở 100 m và 25–60 phút ở 5 km {S01: p.24–25, Fig. 4}.
- [C124] Không có NSE, RMSE, MAE, CSI, R² cho floodGAN hay MIKE+ (NEG) {S01: toàn văn, NEG}.

### I5 Dữ liệu huấn luyện
- [C125] Dữ liệu radar lịch sử DWD RADOLAN huấn luyện GAN sinh mưa, tạo >900 kịch bản mưa lớn tổng hợp cho Aachen {S01: p.11–12, Table 1 AP1}.
- [C126] 160 trận mưa lớn được mô phỏng bằng MIKE (2D, 61 km², bước 5 phút); bản đồ mực nước + raster mưa tạo thành bộ dữ liệu huấn luyện AI {S01: p.11–12, Table 1 AP1}.
- [C127] Radar băng X của KISTERS được hiệu chỉnh với 70 trạm DWD cùng dữ liệu MADIS/CWOP {S01: p.21, "Radardaten"}.

### I6 Kết quả
- [C128] floodGAN cho bản đồ ngập độ phân giải cao "trong vài giây" (§2.6) hoặc "trong vài phút" (§2.4); không có đo thời gian cụ thể {S01: p.51 §2.6; p.49 §2.4}.
- [C129] Chuỗi vận hành tự động (radar nowcast → floodGAN trong KISTERS datasphere) được trình diễn trong sự kiện 02.05.2024 {S01: p.30–31, Fig. 6–7}.
- [C130] Kịch bản giao thông cho cường độ mưa 30/40/47/70 mm/h; ngưỡng độ sâu lội nước ô tô < 0,3 m, xe cứu hộ < 0,6 m {S01: p.35, §2.1.3 e)}.

### I7 Hạ tầng CNTT
- [C131] Phần mềm: Python/PyTorch (AI), MIKE FM/MIKE+ (DHI), pySTEPS, QGIS {S01: p.17, §1.4.2}.
- [C132] Mô phỏng thủy động lực dùng song song GPU (CUDA), rút ngắn từ vài giờ (CPU) xuống giờ–phút {S01: p.26–27, §2.1.3 a)}.
- [C133] floodGAN chạy trên hạ tầng IWW; tích hợp qua KISTERS datasphere (cloud) và RTAF trong Docker trên Linux {S01: p.29, §2.1.3 c)}.
- [C134] Không nêu phần cứng huấn luyện (GPU/CPU), thời gian huấn luyện, số epoch (NEG); chỉ nêu "đầu tư phần cứng kỹ thuật" là khoản chi lớn thứ hai của IWW {S01: p.48, §2.3}.

---

## 2. Bangkok, Thái Lan — Bangkok Flood Management DSS, Mott MacDonald (S02)

### I1
- [C201] Bài trình bày của Sharla McGavock (Mott MacDonald) tại Singapore International Water Week, 19.04.2022 {S02: p.1}.
- [C202] Hệ thống: "Bangkok Flood Management Decision Support System", được giới thiệu là hệ thống dự báo ngập nước mưa thời gian thực "đầu tiên trên thế giới" {S02: p.2}.
- [C203] DSS gồm 3 thành phần: cải thiện mạng radar mưa, machine learning khắc phục giới hạn mô hình thủy lực, tích hợp dữ liệu cảm biến/dự báo/cảnh báo trên nền tảng Moata {S02: p.5}.
- [C204] Ảnh chụp màn hình có lớp bản đồ "Pilot Area", cho thấy triển khai thí điểm; không nêu diện tích/dân số {S02: p.15}.
- [C205] Dữ liệu trạm đo được cấp trực tiếp từ BMA {S02: p.15}.
- [C206] Ảnh chụp cho thấy hệ thống chạy với dữ liệu năm 2021 (27.08.2021; 01–03.10.2021) {S02: p.5, p.9}.
- [C207] Không có diện tích, dân số, kinh phí và thời gian của dự án Bangkok; chỉ có thời lượng của chương trình Global Future Cities ở Đông Nam Á (3 năm, 13 dự án, 9 thành phố, 6 quốc gia) {S02: p.3}; (NEG phần còn lại) {S02: toàn văn, NEG}.

### I2
- [C208] Mô hình thủy lực bao gồm địa hình, sử dụng đất và mạng lưới thoát nước {S02: p.11}.
- [C209] Mạng quan trắc trên Moata: trạm đo mưa, trạm đo mực nước ngập đường, trạm đo mực nước và lưu lượng sông/kênh {S02: p.9}.
- [C210] Không có số liệu chiều dài cống, hố ga, trạm bơm, kênh (NEG) {S02: toàn văn, NEG}.

### I3
- [C211] Mô hình AI là "machine learning surrogate model" mô phỏng thay thế mô hình thủy lực TUFLOW đã hiệu chỉnh {S02: p.10–11}.
- [C212] Đầu vào: mưa; đầu ra: mực nước ngập trên lưới 2D (ML thay thế toàn bộ chuỗi môi trường vật lý + phương trình + TUFLOW) {S02: p.11–12}.
- [C213] Không nêu kiến trúc ML, thời gian dự báo trước (lead time), độ phân giải lưới (NEG) {S02: toàn văn, NEG}.

### I4
- [C214] [Không rõ] "Sai số tương đối 2 cm" của mô hình ML; không định nghĩa tham chiếu, khả năng cao là so với TUFLOW [INF] {S02: p.13}.
- [C215] [Calibration thủy lực] Mô hình thủy lực được gọi là "đã hiệu chỉnh" nhưng không có chỉ số {S02: p.10}.
- [C216] [Hiệu chỉnh đầu vào radar] Biểu đồ hộp r² và bias: "RADAR UNCORRECTEDD" r² trung vị ≈0,66, bias ≈0,58; "GAUGE" r² ≈0,77, bias ≈1,01; "RADAR" (sau cải tiến) r² ≈0,81, bias ≈0,98 (đọc từ hình) {S02: p.8}.
- [C217] Đồ thị chuỗi thời gian "target" vs "pred" tại các ô lưới (events 160625, 161016, 161024, 171002) cho thấy trực quan ML bám sát {S02: p.13}.
- [C218] Không có NSE/RMSE/CSI và không có kiểm định với ngập quan trắc (NEG) {S02: toàn văn, NEG}.

### I5
- [C219] Dữ liệu huấn luyện là kết quả mô phỏng TUFLOW theo các trận mưa (suy ra từ "target" là mô hình thủy lực) [INF dựa trên C211, C217] {S02: p.10–13}.
- [C220] Không có số kịch bản, mưa thiết kế, cách chia tập dữ liệu (NEG) {S02: toàn văn, NEG}.

### I6
- [C221] Mô hình ML cho dự báo ngập trong 1 giây, xuất kết quả mỗi 10 phút {S02: p.13}.
- [C222] Kết quả chính: thông tin ngập thời gian thực, ứng phó chủ động, mở ra cơ hội {S02: p.16}.
- [C223] Tính năng: cấp dữ liệu trực tiếp từ BMA, cổng web riêng tư, bản đồ/hoạt ảnh dự báo, cảnh báo (alarm) {S02: p.15}.
- [C224] Bản đồ so sánh "Machine learning model" vs "Hydraulic model" cho thấy phân bố không gian rất giống nhau; bản đồ ML có nhiều ô sâu hơn một chút; chỉ là so sánh trực quan, thang màu không có đơn vị {S02: p.10}.

### I7
- [C225] Không có thông tin phần cứng, thời gian huấn luyện, framework ML; chỉ nêu TUFLOW và Moata (NEG) {S02: toàn văn, NEG}.

---

## 3. Brisbane / Queensland, Úc — FloodMapp DASH (S03)

### I1
- [C301] Bài trình bày của Juliette Murphy (FloodMapp) tại FIG Working Week 2025, Brisbane, 6–10/04/2025; sản phẩm "FloodMapp DASH", thông tin tác động trực tuyến vận hành cho quản lý khẩn cấp {S03: p.1, p.8}.
- [C302] Tuyên bố có thể mở rộng từ cấp tài sản (property) đến cấp quốc gia {S03: p.8}.
- [C303] Triển khai toàn bang Queensland (tháng 4/2025) với "tới 1400 trạm đo" {S03: p.26}.
- [C304] Lưu vực sông Thomson tại trạm Stonehenge và Retreat rộng 139.000 km² {S03: p.27}.
- [C305] Ví dụ ứng dụng: bão nhiệt đới Alfred (03/2025, SE Queensland gồm các khu Brisbane Nundah, Wilston, Coorparoo), lũ Tây Queensland (03–04/2025), Transport for NSW, Norfolk VA (Mỹ) {S03: pp.12–41}.
- [C306] Không có kinh phí, thời gian dự án, dân số, diện tích đô thị Brisbane (NEG) {S03: toàn văn, NEG}.

### I2
- [C307] Không có thông tin mạng thoát nước (cống, hố ga, trạm bơm); chuỗi mô hình gồm "DASH Hydrologic Model" và "DASH 2D Hydraulic Model" theo mực nước sông (NEG) {S03: p.10}.

### I3
- [C308] AI chỉ được mô tả là "tăng cường thủy văn và thủy lực vật lý bằng AI và Machine learning"; không nêu kiến trúc {S03: p.8}.
- [C309] Đầu vào: mưa trực tiếp, cảm biến ngập, mực nước sông, dữ liệu khí tượng dự báo; cập nhật mỗi giờ {S03: p.8, p.10}.
- [C310] Đầu ra: phạm vi, độ sâu và tác động ngập (ForeCast, NowCast, PostCast), qua API vào GIS {S03: p.8, p.5, p.10}.
- [C311] Độ phân giải không gian 10 m tới 1 m; tuyên bố "property level accuracy" {S03: p.8}.
- [C312] Không nêu lead time; giao diện quản trị có lớp "Model quality 6H/24H/72H" [INF: có thể là các chân trời dự báo] {S03: p.27}.

### I4
- [C313] [Không rõ] Dữ liệu "Calibration & Validation": thủy đồ trạm đo, ảnh truyền thông, video drone, nghiên cứu ngập trước đó, camera giao thông, mạng xã hội, vết lũ, ảnh vệ tinh {S03: p.12}.
- [C314] [Verification sự kiện thực] Sông Thomson tại Stonehenge 03/2025: dự báo đỉnh 7,9 m so với quan trắc 7,4 m (chênh 0,5 m ≈ 7% — tính toán của người tổng hợp) {S03: p.29}.
- [C315] [Verification định tính] So sánh ảnh sự kiện thực với bản đồ mô hình trong bão Alfred và lũ Tây Queensland {S03: pp.17–23, 30–32}.
- [C316] Không có NSE/RMSE/CSI (NEG) {S03: toàn văn, NEG}.

### I5
- [C317] Không nêu bộ dữ liệu huấn luyện; chỉ liệt kê loại dữ liệu "Big Data" (thủy đồ BoM, ảnh vệ tinh, camera, cọc đo độ sâu, cảm biến) và dữ liệu cộng đồng {S03: p.7, p.15}.

### I6
- [C318] Cung cấp qua API WMS/WFS, Esri REST; "24/7 với 99,5% uptime"; tích hợp Waze, QGIS, Esri, HERE, Juvare WebEOC, Genasys {S03: p.11}.
- [C319] Được dùng tại Trung tâm điều phối thảm họa bang Queensland trong bão Alfred, dashboard Transport for NSW, đóng đường/điều hướng ở Norfolk {S03: pp.16, 34–41}.

### I7
- [C320] Không nêu hạ tầng huấn luyện; chỉ hạ tầng phân phối (GeoServer, ArcGIS Enterprise, Esri cloud) (NEG) {S03: p.10, p.27}.

---

## 4. Dorsten, Đức — dự án PuwaSTAR (S04, S05, S06)

### I1
- [C401] Khu thí điểm: trạm bơm Dorsten-Hammbach và vùng polder xung quanh, trong vùng sụt lún do khai thác than {S06: p.5, §1; S05: p.2}.
- [C402] Đối tác: Lippeverband/EGLV (điều phối, Dr. Daniela Falter), Hydrotec, Universität Siegen (FWU); mã tài trợ 13N16800/01/02 {S05: p.1}.
- [C403] Tài trợ bởi BMFTR, chương trình "Anwender – Innovativ: Forschung für die zivile Sicherheit II" {S04: p.1–2}.
- [C404] Thời gian dự án mâu thuẫn giữa các tài liệu: 01.10.2023–31.12.2025 {S05: p.1} so với 01.12.2023–31.12.2025 {S04: p.1}.
- [C405] Trạng thái: tích hợp vào Delft-FEWS của EGLV và đang chạy thử nghiệm (Testbetrieb) {S05: p.3; S04: p.6, p.10}.
- [C406] Mô hình được thu hẹp về khu đô thị chính với ba dòng vào: Hammbach, Wienbach và một nhánh nhỏ {S06: p.15–16, §4.2.1}.
- [C407] Không có diện tích, dân số, số tiền kinh phí (NEG) {S04, S05, S06: toàn văn, NEG}.

### I2
- [C408] Trạm bơm Dorsten-Hammbach có 4 bơm chống lũ, tổng công suất 15,5 m³/s (1×2,0 + 3×4,5 m³/s) {S06: p.15, §4.1.2}.
- [C409] Ảnh màn hình Delft-FEWS thể hiện 6 bơm (M1_0.5, M2_0.5, M3_2.0, M4_4.5, M5_4.5, M6_4.5) và đường công suất tối đa 15,50 m³/s {S04: p.9, Fig. 2-4}. [INF] 15,50 = 2,0 + 3×4,5, nên hai bơm 0,5 m³/s không tính vào công suất tối đa — phù hợp với 4 bơm chống lũ trong S06 (dựa trên C408, C409).
- [C410] Mô hình liên kết 1D/2D: SWMM (1D, mạng cống kể cả trạm bơm, phương trình Saint-Venant) + P-DWave (2D, sóng khuếch tán song song) {S06: p.9, §3.2.2}.
- [C411] Mô hình 2D có độ phân giải 5 m {S06: p.10, §3.2.2}.
- [C412] Mô hình thủy văn mưa–dòng chảy NASIM cho Hammbach {S04: p.7, §2.4 (AP 4.1)}.
- [C413] Không có chiều dài cống, số hố ga, số đoạn cống (NEG) {S06: toàn văn, NEG}.

### I3
- [C414] Kiến trúc: CNN dựa trên ResNet18, mô hình thay thế (surrogate) cho mô hình thủy động lực, với cách huấn luyện "feature-informed" {S06: p.10, §3.2.3, Fig 3-1}.
- [C415] Hai nhánh song song cho mưa (tensor (n,17,17,2)) và lưu lượng (n,17,17,4); đầu ra cộng theo phần tử rồi qua các lớp 256, 512, n nơ-ron {S06: p.10, §3.2.3}.
- [C416] Đầu vào: mưa/lưu lượng dự báo 24 h tới + giá trị tích lũy 24 h qua + công suất bơm khả dụng {S06: p.11; S04: p.6, §2.3}.
- [C417] Đầu ra: độ sâu ngập lớn nhất mỗi ô trong 24 h tới, bản đồ 5 × 5 m {S06: p.10; S04: p.8, §2.4}.
- [C418] Chân trời dự báo 24 h, cửa sổ trượt 6 h {S06: p.11, Fig 3-2}.
- [C419] 8 mô hình riêng cho 8 kịch bản sự cố bơm (công suất còn lại 15,5 → 0 m³/s) {S06: p.15, Table 2; S04: p.8}.
- [C420] Mạng Bayes tính xác suất sự cố bơm {S06: p.7–8, §3.1.2}.
- [C421] Mưa dự báo từ tổ hợp ICON-D2-EPS (20 thành viên, cập nhật 3 h); chạy 3 lần AI theo phân vị 10/50/90% {S04: p.7–8, §2.4}.
- [C422] Tự động chạy khi lưu lượng dự báo tại trạm "Am Strandbad" vượt ngưỡng, lặp mỗi 6 h {S04: p.8, §2.4}.

### I4
- [C423] [Calibration thủy lực] Tiêu chí kiểm định mô hình 1D/2D: không quá tải ở T = 5 năm (DWA A 118), so sánh thể tích bơm đo được cho 5 sự kiện, so với bản đồ nguy cơ mưa lớn chính thức {S06: p.9, §3.2.2}.
- [C424] [Calibration thủy lực] Thể tích bơm tái tạo "một phần tới 97%"; tái tạo được bản đồ nguy cơ mưa lớn chính thức {S06: p.15–16, §4.2.1}.
- [C425] [Verification AI trên sự kiện mô phỏng độc lập] 56 sự kiện kiểm tra (1111 cửa sổ dự báo): RMSE 0,024–0,044 m; MAE 0,007–0,010 m; CSI > 0,95 (tối đa 0,967); RVE 0,002–0,011 {S06: p.16, §4.2.2}.
- [C426] RMSE theo ô < 0,05 m ở phần lớn lưu vực; 0,20–0,25 m tại trạm bơm (điểm thấp nhất) {S06: p.17–18, Fig 4-3}.
- [C427] RMSE theo bước thời gian không vượt 0,1 m; CSI trung bình ≈ 0,96 {S06: p.18, Fig 4-4}.
- [C428] Tham chiếu cho kiểm tra AI là mô hình thủy động lực, không phải ngập quan trắc {S06: p.12, Table 1 (RVE vs hydrodynamic reference)}.
- [C429] Không báo cáo tách tập train/validation (NEG) {S06: toàn văn, NEG}.

### I5
- [C430] Mưa huấn luyện (bước 5 phút): 73 trận lịch sử (1950–2023), 168 trận mưa thiết kế (chu kỳ lặp 5–200 năm, thời đoạn 3–96 h, DWA A 531), 375 trận từ 134 kịch bản khí hậu (RCP 4.5, 8.5) {S06: p.8–9, §3.2.1}.
- [C431] Độ sâu ngập mục tiêu sinh từ mô hình P-DWave/SWMM; lưu lượng đầu vào từ mô hình thủy văn {S06: p.9, §3.2.2; p.6, §2}.
- [C432] Xác suất sự cố bơm dựa trên tài liệu và bảng hỏi 17 câu với 10 nhà vận hành trạm bơm lớn {S06: p.7, §3.1.1}.

### I6
- [C433] Thời gian tính "vài giây đến tối đa vài phút"; suy luận trên CPU đủ cho vận hành {S06: p.13, §3.3; p.24, §5}.
- [C434] Dự báo tốt ở pha lũ lên; sai số lớn hơn ở pha rút và với sự kiện cực đoan hiếm {S06: p.19–21, Fig 4-6–4-8}.
- [C435] Mô hình chỉ áp dụng cho lưu vực này; lưu vực khác cần mô hình thủy lực và mô phỏng riêng {S06: p.24–25, §5}.
- [C436] Tự động tạo báo cáo tình hình (3 bản đồ ngập, trạng thái trạm đo, trạm bơm, mưa) {S04: p.9, §2.4–2.5}.
- [C437] Mã nguồn công bố trên GitHub (FWUSiegen/PuwaSTAR-) {S05: p.3; S04: p.10–11}.

### I7
- [C438] Mua một máy tính mới để huấn luyện do nhu cầu tính toán lớn (khoản 0850), không nêu cấu hình {S06: p.24, §5}.
- [C439] Adapter mô hình chạy trong Docker trên máy chủ Linux riêng; Python, NumPy, netCDF CF-1.6 {S04: p.6–7, §2.3–2.4}.
- [C440] Không nêu GPU, thời gian huấn luyện, framework học sâu (NEG) {S06, S04: toàn văn, NEG}.

---

## 5. Gelsenkirchen, Đức — KIWaSuS / GE-warnt (S07)

### I1
- [C501] Tiểu dự án GE-warnt thuộc dự án KIWaSuS, tài trợ BMBF (FKZ 13N15560), đơn vị nhận: Abwassergesellschaft Gelsenkirchen (AGG), 01.04.2021–31.03.2024 {S07: p.1, p.4}.
- [C502] Đối tác: HRW (điều phối — theo Fig. 1, p.9), GELSENWASSER AG, AGG, UDE, fuseki/neusta; đối tác liên kết gồm cứu hỏa Gelsenkirchen, LANUV, EG/LV, LAMBRECHT meteo, Provinzial {S07: p.8, §2.2; p.9, Fig. 1}.
- [C503] Khu nghiên cứu: lưu vực cống số 3.219, Gelsenkirchen-Ückendorf {S07: p.10, §3.1; p.11, Fig. 2}.
- [C504] Hệ thống chỉ được xây dựng cho một phần thành phố; mở rộng toàn thành phố cần mở rộng mô hình và mạng cảm biến {S07: p.24, §5}.
- [C505] Trạng thái demonstrator, thử nghiệm bằng sự kiện mô phỏng quá khứ; buổi thử chung tháng 1/2024 {S07: p.21, §3.3.3; p.13}.
- [C506] Không nêu số tiền kinh phí {S07: p.22, §4.1}.

### I2
- [C507] Dữ liệu nền từ AGG: bản đồ nguy cơ mưa lớn, dữ liệu mạng cống, sử dụng đất, DGM — làm cơ sở cho mô hình mạng cống và mô hình dòng chảy mặt {S07: p.11–12, §3.1}.
- [C508] Lắp lưu lượng kế MID trong cống và trạm đo mưa theo chuẩn DWD, cùng cảm biến giá rẻ {S07: p.11, §3.1}.
- [C509] Không có số liệu chiều dài cống, hố ga, trạm bơm, diện tích (NEG) {S07: toàn văn, NEG}.

### I3
- [C510] Mục tiêu: hệ thống cảnh báo thời gian thực cho lũ quét đô thị dùng AI, đặc biệt là machine learning {S07: p.7, §2.1}.
- [C511] Chuỗi: hiệu chỉnh radar thời gian thực → mô hình dự báo mưa → mô hình dự báo quá tải cống → mô hình dự báo vùng ngập → dashboard/WMS {S07: p.12, Fig. 3}.
- [C512] Chân trời dự báo 0,5–2 h {S07: p.23, §4.3.1}.
- [C513] Thời gian cảnh báo đạt được khoảng 60 phút {S07: p.20, §3.3.2; p.26, §5}.
- [C514] Đầu ra theo bước 5 phút (lớp 10–60 phút) {S07: p.17, Fig. 6}.
- [C515] Không nêu kiến trúc ML, độ phân giải không gian (NEG) {S07: toàn văn, NEG}.

### I4
- [C516] [Không rõ — định tính] Mô phỏng một sự kiện quá khứ, so với điểm can thiệp của cứu hỏa: "gute Übereinstimmung" cho cả sự kiện, minh họa tại ba vị trí {S07: p.21, §3.3.3; Fig. 8 p.22}.
- [C517] [Không rõ — định tính] Điểm nóng dự báo "nahezu deckungsgleich" với bản đồ nguy cơ tĩnh {S07: p.21, §3.3.3}.
- [C518] Hiển thị chất lượng mô hình chỉ là tính năng tương lai {S07: p.16, §3.3.1.2}.
- [C519] Không có chỉ số định lượng và không có calibration; chỉ có đánh giá định tính so với điểm can thiệp cứu hỏa (xem C516) {S07: toàn văn; p.21–22, §3.3.3}.

### I5
- [C520] Đầu vào: mưa radar, mưa trạm đo mặt đất, cấp lưu lượng đo trong cống (MID và cảm biến giá rẻ) {S07: p.12, Fig. 3; p.11}.
- [C521] Không mô tả bộ dữ liệu huấn luyện (NEG) {S07: toàn văn, NEG}.

### I6
- [C522] Bàn giao: nền tảng dữ liệu, ứng dụng chuyên gia, dịch vụ WMS tích hợp Geoportal thành phố và hệ thống thông tin cứu hỏa {S07: p.14–15, Fig. 4; p.17}.
- [C523] Khái niệm cảnh báo: cảnh báo sơ bộ (DWD) + 3 cấp; cấp 2 khi ít nhất một điểm nóng dự báo vượt 25 cm {S07: p.19–20, Fig. 7}.
- [C524] 60 phút quá ngắn cho biện pháp phòng ngừa; cứu hỏa cần ít nhất 6 h để sơ tán {S07: p.18–19, §3.3.1.3}.
- [C525] Không có số liệu thời gian tính, tỷ lệ báo động giả (NEG) {S07: toàn văn, NEG}.

### I7
- [C526] Không nêu phần cứng, thời gian huấn luyện, framework (NEG) {S07: toàn văn, NEG}.

---

## 6. Hong Kong — Drainage Services Department (S08, S09)

### I1
- [C601] DSD dùng/phát triển hai hệ thống AI: AI Flood Monitoring System và Smart Flood Forecast and Alert System {S08: p.1}.
- [C602] Smart Flood Forecast and Alert System phát triển cùng South China University of Technology; thử nghiệm giữa 2026 tại 3 điểm: sông Lam Tsuen (Tai Po), Wan Chai, sông Tsui Ping (Kwun Tong) {S08: p.2}.
- [C603] Chi phí phát triển ước khoảng 1,3 triệu $ (đơn vị "$" trong tài liệu, HK$), bao gồm chi vận hành 3 điểm thử nghiệm năm 2026-27 {S08: p.2}.
- [C604] AI Flood Monitoring System phát triển 2024 cùng HKUST; thí điểm tại Chatham Road South (Tsim Sha Tsui), Tai Kiu Tsuen và Tung Tau Wai Village (Yuen Long) {S08: p.2}.
- [C605] Mở rộng cùng Cảnh sát HK: kết nối hơn 300 camera CCTV thuộc sáng kiến "SmartView" {S08: p.2}.
- [C606] Chi phí phát triển khoảng 6 triệu $ (HK$), chi vận hành ~1,4 triệu $/năm {S08: p.2}.
- [C607] Mosaic Model Map (M³) do DSD tự phát triển năm 2024, vận hành từ 2025, không phát sinh chi phí bổ sung {S08: p.2}.
- [C608] Hệ thống Hydrometric Information System + thiết bị giám sát ngập: chi vận hành ~4 triệu $ năm 2025-26 {S09: p.2}.

### I2
- [C609] Hydrometric Information System: tổng cộng hơn 300 cảm biến mực nước và trạm đo mưa, giám sát mực nước sông chính/kênh thoát nước và lượng mưa các quận {S09: p.1}.
- [C610] Từ 2024 lắp hơn 100 "Flood Monitoring Devices" đo mực nước trên đường {S09: p.2}.
- [C611] Không có thông tin mạng cống (NEG) {S08, S09: toàn văn, NEG}.

### I3
- [C612] AI Flood Monitoring System dùng mô hình ngôn ngữ–thị giác lớn (large vision-language model) phân tích ảnh camera đường phố để phát hiện ngập, gửi cảnh báo tức thì {S08: p.2}.
- [C613] Smart Flood Forecast and Alert System tích hợp "big data và công nghệ AI tiên tiến"; không mô tả kiến trúc {S08: p.2}.
- [C614] M³ là "hệ thống rủi ro ngập toàn lãnh thổ thời gian thực" nhằm khắc phục thời gian tính dài của mô hình thủy lực truyền thống; không được gọi là AI {S08: p.2}.

### I4
- [C615] Không có chỉ số độ chính xác (NEG) {S08, S09: toàn văn, NEG}.

### I5
- [C616] Không mô tả dữ liệu huấn luyện; dữ liệu vận hành: ảnh CCTV, cảm biến {S08: p.2; S09: p.1–2}.

### I6
- [C617] DSD nêu rằng năm 2025 phần lớn các vụ ngập được xử lý trong 1–2 giờ (con số vận hành chung của DSD, không quy trực tiếp cho hệ thống AI, không có mốc so sánh) {S09: p.2}.
- [C618] M³ được dùng dự báo rủi ro ngập vùng ven biển trũng thấp hoặc khu dân cư lộng gió trước bão mạnh/siêu bão {S08: p.2; S09: p.2}.

### I7
- [C619] Không có thông tin hạ tầng CNTT (NEG) {S08, S09: toàn văn, NEG}.

---

## Kết luận (placeholder)

## Bảng bao phủ checklist

| Item | Aachen | Bangkok | Brisbane | Dorsten | Gelsenkirchen | Hong Kong |
|---|---|---|---|---|---|---|
| I1 | C101–C109 | C201–C207 | C301–C306 | C401–C407 | C501–C506 | C601–C608 |
| I2 | C110–C113 | C208–C210 | C307 (NEG) | C408–C413 | C507–C509 | C609–C611 |
| I3 | C114–C119 | C211–C213 | C308–C312 | C414–C422 | C510–C515 | C612–C614 |
| I4 | C120–C124 | C214–C218 | C313–C316 | C423–C429 | C516–C519 | C615 (NEG) |
| I5 | C125–C127 | C219–C220 | C317 | C430–C432 | C520–C521 | C616 |
| I6 | C128–C130 | C221–C224 | C318–C319 | C433–C437 | C522–C525 | C617–C618 |
| I7 | C131–C134 | C225 (NEG) | C320 (NEG) | C438–C440 | C526 (NEG) | C619 (NEG) |

Các mục NEG là giới hạn của tài liệu được cung cấp (user-provided corpus), không phải lỗ hổng tìm kiếm; người dùng yêu cầu chỉ tổng hợp từ `docs/`.
