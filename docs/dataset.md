# Standardized CSV Dataset Schema

This document defines the **input dataset schema** for the Delft3D FM conversion submodule.
The standardized CSVs are produced by drawing tools (see `src/tools/gis_template.py`,
`src/tools/gpkg_to_csv.py`) and consumed verbatim by the conversion pipeline.

**Key conventions:**

- **CRS in:** EPSG:4326 (WGS84). All coordinate columns and GeoJSON geometry strings use WGS84.
  The conversion pipeline reprojects to a projected metric CRS at build time (default EPSG:32648 / UTM 48N).
- **Field names:** English, max 10 characters (shapefile DBF compatibility).
- **Required fields** are marked with `*`.
- **Geometry encoding:** Polygon shapes use a GeoJSON string in the `Shape` column.
  Line geometries (rivers, canals, sewers) use GeoJSON LineString in the `RouteShape` column.
- **Standardization code is not part of this repo.** The standardization submodule lives in the
  SWMM repo (`G:/workspace/github/swmm`). Only the schema is migrated here so the conversion
  can document what it expects to receive.
- **Dataset folder names are kept Vietnamese** to match the drawing convention:
  - `thoat_nuoc/` — sewer/urban drainage components (sewers, manholes, pumps, weirs, orifices, outfalls)
  - `mang_luoi_song_ho_kenh_muong/` — river/lake/canal network (rivers, canals, lakes)
  - `thuy_van/` — hydrology/meteorology (hyetographs, rainfall timeseries, landuses)

---

## Common Metadata Fields (shared by all components)

| Field Name | Type | Width | Description | Source mapping |
|------------|------|-------|-------------|----------------|
| `ID` | Integer | 10 | Unique feature identifier | stt / stt_id / OBJECTID |
| `Name` | String | 150 | Feature name | TenCongDap / TenKenhMuong / Name1 etc. |
| `Location` | String | 150 | Address / place description | DiaDiem / DiaChi |
| `Province` | String | 50 | Province/City | Tinh/Thanh pho |
| `District` | String | 50 | District | Quan/Huyen |
| `Ward` | String | 50 | Ward/Commune | Phuong/Xa |
| `Manager` | String | 80 | Managing organization | DonViQuanLy / Ma don vi quan ly |
| `YearBuilt` | Integer | 5 | Year of construction/commissioning | NamSuDung |
| `YearUpdate` | Integer | 5 | Year data was last updated | NamCapNhat |
| `Status` | String | 30 | Operational status | Tinh trang hoat dong / Status |
| `Notes` | String | 254 | Remarks | GhiChu |

---

## Group 1: Topography / Spatial

### 1.1 Subcatchment

**Geometry:** Polygon | **Source datasets:** generated sample data

| Field Name | Type | Width | Description |
|------------|------|-------|-------------|
| `ID`* | Integer | 10 | Feature ID |
| `Name`* | String | 150 | Subcatchment name |
| `RainGage`* | String | 150 | Name of rain gage (references raingages.csv) |
| `OutletLon`* | Real | 12 | Outlet point longitude (WGS84) |
| `OutletLat`* | Real | 12 | Outlet point latitude (WGS84) |
| `SewerRoute` | String | 150 | Name of sewer/canal route the outlet belongs to (informational) |
| `Area_ha`* | Real | 12 | Subcatchment area (ha) |
| `Imperv_pct` | Real | 10 | Percent impervious (%) |
| `Width_m` | Real | 10 | Characteristic width (m) |
| `Slope_pct` | Real | 10 | Average surface slope (%) |
| `CurbLen_m` | Real | 10 | Curb length (m) |
| `N_Imperv` | Real | 10 | Manning's N for impervious area |
| `N_Perv` | Real | 10 | Manning's N for pervious area |
| `S_Imperv_mm` | Real | 10 | Depression storage, impervious (mm) |
| `S_Perv_mm` | Real | 10 | Depression storage, pervious (mm) |
| `PctZero` | Real | 10 | Percent of impervious area with zero storage (%) |
| `RouteTo` | String | 20 | Internal routing (OUTLET / IMPERVIOUS / PERVIOUS) |
| `PctRouted` | Real | 10 | Percent routed (%) |
| `InfMethod` | String | 30 | Infiltration method (MODIFIED_GREEN_AMPT, HORTON, etc.) |
| `SuctHead_mm` | Real | 10 | Suction head (mm) — Green-Ampt |
| `Conductiv_mmh` | Real | 10 | Hydraulic conductivity (mm/hr) — Green-Ampt |
| `InitDef` | Real | 10 | Initial moisture deficit — Green-Ampt |
| `Shape` | String | — | Polygon boundary as GeoJSON |

---

## Group 2: River, Lake, and Canal Network

### 2.1 River

**Geometry:** LineString | **File:** `mang_luoi_song_ho_kenh_muong/rivers.csv`

| Field Name | Type | Width | Description | River SHP | rawdata.csv |
|------------|------|-------|-------------|-----------|-------------|
| `ID`* | Integer | 10 | Feature ID | OBJECTID | - |
| `Name` | String | 150 | River name | Name | Ten muong, song |
| `Code` | String | 20 | River/waterway code | Code | Ma muong/song |
| `Strahler`* | Integer | 5 | Stream order (Strahler) | Strahler | - |
| `Length_m`* | Real | 12 | Segment length (m) | Length | Chieu dai (m) |
| `Width_m` | Real | 10 | Average width (m) | - | Chieu rong trung binh (m) |
| `BedElev_m` | Real | 10 | Bed elevation (m) | - | - |
| `BankElev_m` | Real | 10 | Bank elevation (m) | - | - |
| `FlowDir` | String | 20 | Flow direction | - | Huong chay |
| `FromNode`* | String | 20 | Start node ID of the route | - | Diem bat dau |
| `ToNode`* | String | 20 | End node ID of the route | - | Diem ket thuc |
| `RouteShape` | String | 254 | Route path as GeoJSON LineString | - | - |
| `XSType` | String | 30 | Cross-section profile type (TRAPEZOIDAL, IRREGULAR, etc.) | - | - |
| `Material` | String | 40 | Lining material | - | Chat lieu |
| `Basin` | String | 80 | River basin name | - | - |
| `IrrigSys` | String | 120 | Irrigation system name | - | He thong thu gom |

### 2.2 Canal / Ditch

**Geometry:** LineString | **File:** `mang_luoi_song_ho_kenh_muong/canals.csv`

| Field Name | Type | Width | Description | Canal CSV | rawdata |
|------------|------|-------|-------------|-----------|---------|
| `ID`* | Integer | 10 | Feature ID | stt_id | Ma muong/song |
| `Name`* | String | 150 | Canal/ditch name | TenKenhMuong | Ten ranh |
| `Type` | String | 30 | Canal/Ditch | - | Loai ranh |
| `Length_m`* | Real | 12 | Length (m) | ChieuDai | Chieu dai (m) |
| `Width_m` | Real | 10 | Width (m) | BeRongKenh | Chieu rong trung binh (m) |
| `BedElev_m` | Real | 10 | Bed elevation (m) | CaoTrinhDayKenh | Cao do day ranh (m) |
| `LeftBank` | String | 30 | Left bank elevation | CaoTrinhBoTrai | - |
| `RightBank` | String | 30 | Right bank elevation | CaoTrinhBoPhai | - |
| `SlopCoef` | String | 20 | Side slope coefficient | HeSoMai | Do doc (%) |
| `Material` | String | 40 | Lining material/structure | KetCauCongTrinh | Chat lieu |
| `Grade` | String | 10 | Infrastructure grade (I-IV) | CapCongTrinh | - |
| `Purpose` | String | 60 | Function (irrigation/drainage) | MucTieuNhiemVu | - |
| `SvcArea` | Real | 12 | Service area (ha) | DienTichPhucVu | - |
| `IrrigSys` | String | 120 | Parent irrigation system | HeThongCongTrinhThuyLoi | Ma he thong thu gom |
| `FlowDir` | String | 20 | Flow direction | - | Huong tuyen thoat nuoc |
| `FromNode`* | String | 20 | Start node ID of the route | - | Diem bat dau |
| `ToNode`* | String | 20 | End node ID of the route | - | Diem ket thuc |
| `RouteShape` | String | 254 | Route path as GeoJSON LineString | Shape | - |
| `XSType` | String | 30 | Cross-section profile type | - | Mat cat dien hinh |
| `WtrLevel` | Real | 10 | Design water level (m) | - | Cao do muc nuoc (m) |
| `XSArea` | Real | 10 | Cross-section area (m2) | - | Tiet dien (m2) |

### 2.3 Lake / Detention Pond

**Geometry:** Point (centroid) | **File:** `mang_luoi_song_ho_kenh_muong/lakes.csv`

| Field Name | Type | Width | Description | rawdata |
|------------|------|-------|-------------|---------|
| `ID`* | Integer | 10 | Feature ID | Ma ho dieu hoa |
| `Name`* | String | 150 | Lake/pond name | Ten ho dieu hoa |
| `Group` | String | 40 | Lake group classification | Nhom ho |
| `Area_ha`* | Real | 12 | Surface area (ha) | Dien tich ho ung voi dinh bo ke (ha) |
| `BedArea_ha` | Real | 12 | Bottom area (ha) | Dien tich day ho (ha) |
| `Vol_m3`* | Real | 15 | Storage volume (m3) | Dung tich ho ung voi dinh bo ke (m3) |
| `BedElev_m`* | Real | 10 | Bottom elevation (m) | Cao do day (m) |
| `CrestElv` | Real | 10 | Embankment crest elev (m) | Cao do dinh bo ke (m) |
| `BankElev_m` | Real | 10 | Grass bank elevation (m) | Cao do bo co (m) |
| `NatWtrLvl` | Real | 10 | Natural water level (m) | Cao do muc nuoc tu nhien (m) |
| `WetLvl_m` | Real | 10 | Wet season control level (m) | Muc nuoc khong che mua mua (m) |
| `DryLvl_m` | Real | 10 | Dry season control level (m) | Muc nuoc khong che mua kho (m) |
| `NumInlets` | Integer | 5 | Number of inlet/outlet structures | So luong cua cong ra vao ho |
| `Perim_m` | Real | 12 | Perimeter at crest (m) | Chu vi ung voi dinh bo ke (m) |
| `IrrigSys` | String | 120 | Parent drainage system | Ma he thong thu gom |
| `Shape` | String | — | Point geometry as GeoJSON |

### 2.4 Mekong Dams

**Geometry:** Point | **Note:** Not converted to Delft3D FM (different geographic region).

| Field Name | Type | Width | Description |
|------------|------|-------|-------------|
| `ID`* | Integer | 10 | Feature ID |
| `Name`* | String | 150 | Dam name |
| `River` | String | 80 | River name |
| `Basin` | String | 80 | River basin |
| `Length_m` | Real | 10 | Dam length (m) |
| `Height_m` | Real | 10 | Dam height (m) |
| `Cap_MW` | Real | 12 | Power capacity (MW) |
| `Vol_Mm3` | Real | 12 | Reservoir volume (million m3) |
| `Catch_km2` | Real | 12 | Catchment area (km2) |
| `Elev_m` | Real | 10 | Site elevation (m) |
| `Purpose` | String | 100 | Function/purpose |
| `SvcArea` | Real | 12 | Service area (km2) |
| `Country` | String | 40 | Country |
| `Complete` | Integer | 5 | Completion year |

---

## Group 3: Urban Drainage System

### 3.1 Sewer Network (Conduits)

**Geometry:** LineString | **File:** `thoat_nuoc/sewers.csv`

| Field Name | Type | Width | Description | rawdata |
|------------|------|-------|-------------|---------|
| `ID`* | Integer | 10 | Feature ID | - |
| `Name`* | String | 150 | Sewer route name | Ten tuyen cong/ranh thoat nuoc |
| `Type` | String | 30 | Classification code | Ma phan loai |
| `Diam_mm`* | Real | 10 | Diameter (mm) for circular | Duong kinh (mm) |
| `Size_mm` | String | 30 | Dimensions (mm) for non-circular (WxH or W*H) | Kich thuoc (mm) |
| `Length_m`* | Real | 12 | Length (m) | Chieu dai (m) |
| `Material` | String | 40 | Pipe material (concrete, PVC, etc.) | Chat lieu |
| `XSArea` | Real | 10 | Cross-section area (m2) | Tiet dien (m2) |
| `FlowDir` | String | 20 | Flow direction | Huong tuyen thoat nuoc |
| `FromNode`* | String | 20 | Upstream node ID | Diem bat dau |
| `ToNode`* | String | 20 | Downstream node ID | Diem ket thuc |
| `RouteShape` | String | 254 | Route path as GeoJSON LineString | - |
| `XSType` | String | 30 | Cross-section profile type (CIRCULAR, RECT_CLOSED, etc.) | Hinh dang |
| `StreetID` | String | 30 | Street number | So hieu duong |
| `DrainZone` | String | 30 | Drainage zone code | Ma vung thoat nuoc |
| `Catchment` | String | 30 | Catchment code | Ma luu vuc thoat nuoc |

### 3.2 Manholes (Ho ga)

**Geometry:** Point | **File:** `thoat_nuoc/manholes.csv`

| Field Name | Type | Width | Description | rawdata |
|------------|------|-------|-------------|---------|
| `ID`* | Integer | 10 | Feature ID | - |
| `Name`* | String | 150 | Manhole name | Ten ho ga |
| `Type` | String | 30 | Manhole type | Ma phan loai ho ga |
| `Area_m2` | Real | 10 | Manhole area (m2) | Dien tich ho ga (m2) |
| `Size_m` | String | 30 | Manhole dimensions (m) | Kich thuoc ho ga (m) |
| `CoverType` | String | 40 | Cover type | Chung loai nap ho ga |
| `InvElev_m`* | Real | 10 | Invert elevation (m) | Cao do day ga (m) |
| `RimElev_m`* | Real | 10 | Rim/ground elevation (m) | Cao do mat duong (m) |
| `SewerLine` | String | 80 | Name of the connected sewer route | Ten tuyen thoat nuoc |
| `StreetID` | String | 30 | Street number | So hieu duong |
| `DrainZone` | String | 30 | Drainage zone code | Ma vung thoat nuoc |
| `Catchment` | String | 30 | Catchment code | Ma luu vuc thoat nuoc |
| `Width` | Real | 10 | Inlet opening width (m) — for 1D-2D inlet | - |
| `Length` | Real | 10 | Inlet opening length (m) — for 1D-2D inlet | - |
| `InletDepth` | Real | 10 | Inlet depth (m) — for 1D-2D inlet | - |
| `InletEffic` | Real | 10 | Inlet efficiency (0-1) — for 1D-2D inlet | - |
| `Shape` | String | — | Point geometry as GeoJSON |

### 3.3 Pumping Stations (Tram bom)

**Geometry:** Point | **File:** `thoat_nuoc/pumps.csv`

| Field Name | Type | Width | Description | TRAMBOM CSV | rawdata |
|------------|------|-------|-------------|-------------|---------|
| `ID`* | Integer | 10 | Feature ID | stt_id | Ma tram |
| `Name`* | String | 150 | Station name | TenTramBom | Ten tram |
| `Source` | String | 80 | Source node supplying water to pump | - | - |
| `SewerLine` | String | 80 | Sewer route the pump supplies water to | - | - |
| `Type` | String | 30 | Station type/classification | Loai | Ma phan loai |
| `Grade` | String | 10 | Station grade | - | Cap tram |
| `NumPumps` | Integer | 5 | Number of pumps | - | So luong bom |
| `Cap_m3s`* | String | 30 | Pump capacity (m3/s) | CongSuat | Cong suat bom (m3/s) |
| `InElev_m` | Real | 10 | Inlet elevation (m) | - | Cao do dau vao (m) |
| `OutElev_m` | Real | 10 | Outlet elevation (m) | - | Cao do dau ra (m) |
| `AutoMonit` | String | 10 | Auto water level monitoring? | - | Theo doi muc nuoc tu dong |
| `TrashScr` | String | 40 | Trash screen system | - | He thong cao rac/song chan rac |
| `Purpose` | String | 100 | Function/purpose | MucTieuNhiemVu | - |
| `SvcArea` | Real | 12 | Service area (ha) | DienTichPhucVu_ha | - |
| `IrrigSys` | String | 120 | Irrigation system | HeThongCongTrinhThuyLoi | Ma he thong thu gom |
| `StreetID` | String | 30 | Street number | - | So hieu duong |
| `Shape` | String | — | Point geometry as GeoJSON |

### 3.4 Weir / Water Regulating Culvert (Cong dap)

**Geometry:** Point | **File:** `thoat_nuoc/weir.csv`

All water regulating culverts are merged into `weir.csv`. The `Type` field distinguishes structure types.

| Field Name | Type | Width | Description | CONGDAP | CONGDUOIDE |
|------------|------|-------|-------------|---------|------------|
| `ID`* | Integer | 10 | Feature ID | stt | stt_id |
| `Name`* | String | 150 | Structure name | TenCongDap | TenCongDap |
| `Type` | String | 60 | Structure type | LoaiCongTrinh | LoaiCongTrinh |
| `Form` | String | 60 | Structure form | HinhThuc | HinhThuc |
| `Chainage` | String | 40 | Chainage/station | LyTrinh | - |
| `River` | String | 80 | River name | - | - |
| `Basin` | String | 80 | River basin | - | - |
| `Length_m` | Real | 10 | Structure length (m) | ChieuDai | ChieuDai |
| `Width_m` | Real | 10 | Structure width (m) | BeRong | BeRong |
| `Height_m` | Real | 10 | Structure height (m) | ChieuCao | ChieuCao |
| `Diam_m` | Real | 10 | Diameter (m) | DuongKinh | DuongKinh |
| `Openings` | Integer | 5 | Number of openings | SoCua | SoCua |
| `InvElev_m`* | Real | 10 | Invert elevation (m) | CaoTrinhDayCong | CaoTrinhDayCong |
| `CrestElv` | Real | 10 | Crown/crest elevation (m) | CaoTrinhDinhCong | CaoTrinhDinhCong |
| `Grade` | String | 10 | Infrastructure grade | CapCongTrinh | - |
| `Operation` | String | 60 | Operation mode | HinhThucVanHanh | HinhThucVanHanh |
| `Purpose` | String | 100 | Function/purpose | MucTieuNhiemVu | MucTieuNhiemVu |
| `Receiver` | String | 80 | Receiving water body | - | Nguon tiep nhan |
| `SvcArea` | Real | 12 | Service area (ha) | DienTichPhucVu_ha | - |
| `IrrigSys` | String | 120 | Irrigation system | HeThongCongTrinhThuyLoi | - |
| `Shape` | String | — | Point geometry as GeoJSON |

### 3.5 Orifices / Control Gates (Cong kiem soat trieu)

**Geometry:** Point | **File:** `thoat_nuoc/orifices.csv`

| Field Name | Type | Width | Description | CONGKIEMSOATTRIEU CSV |
|------------|------|-------|-------------|----------------------|
| `ID`* | Integer | 10 | Feature ID | stt |
| `Name`* | String | 150 | Gate name | TenCongDap |
| `Source` | String | 80 | Upstream sewer/canal feeding the orifice | - |
| `Position` | String | 80 | Location description | ViTri |
| `Type` | String | 60 | Structure type | LoaiCongTrinh |
| `Form` | String | 60 | Orifice shape (CIRCULAR/RECT_CLOSED) | HinhThuc |
| `Length_m` | Real | 10 | Length (m) | ChieuDai |
| `Width_m` | Real | 10 | Width (m) | BeRong |
| `Height_m` | Real | 10 | Height (m) | ChieuCao |
| `Openings`* | Integer | 5 | Number of openings | SoCua |
| `InvElev_m`* | Real | 10 | Invert elevation (m) | CaoTrinhDayCong |
| `CrestElv` | Real | 10 | Crown elevation (m) | CaoTrinhDinhCong |
| `DischCoef` | Real | 10 | Discharge coefficient | - |
| `ClearSpan` | String | 40 | Clear span dimensions | CC_KhauDo_m |
| `SillElev` | String | 20 | Sill elevation | CC_CaoTrinhNguong_m |
| `GateMtrl` | String | 60 | Gate material | CC_LoaiVatLieuCuaVan |
| `GateCtrl` | String | 60 | Gate control mechanism | CC_KieuDongMoCuaVan |
| `Purpose` | String | 200 | Function/purpose | MucTieuNhiemVu |
| `Receiver` | String | 80 | Receiving water body | - |
| `SvcArea` | Real | 12 | Service area (ha) | DienTichPhucVu_ha |
| `Grade` | String | 10 | Infrastructure grade | CapCongTrinh |
| `Shape` | String | — | Point geometry as GeoJSON |

### 3.6 Outfall / Discharge Point (Cua xa)

**Geometry:** Point | **File:** `thoat_nuoc/outfalls.csv`

| Field Name | Type | Width | Description | rawdata.csv |
|------------|------|-------|-------------|-------------|
| `ID`* | Integer | 10 | Feature ID | Ma cua xa |
| `Name`* | String | 150 | Outfall name | Ten cua xa |
| `Type` | String | 30 | Outfall type (FREE/NORMAL/FIXED/TIDAL/TIMESERIES) | Ma phan loai cua xa |
| `Elev_m` | Real | 10 | Invert elevation (m) | Cao do day cua xa (m) |
| `FixedStage` | Real | 10 | Fixed water stage for FIXED type (m) | Cao do muc nuoc thiet ke (m) |
| `FlapGate` | String | 10 | Has flap gate (YES/NO) | Loai cua phai |
| `Receiver` | String | 80 | Receiving water body | Nguon tiep nhan |
| `SewerLine` | String | 80 | Connected sewer/drainage route | Ma tuyen thoat nuoc |
| `Shape` | String | — | Point geometry as GeoJSON |

---

## Group 4: Hydrology / Meteorology

### 4.1 Hyetograph Stations

**Geometry:** Point | **GPKG table:** `hyetograph`

| Field Name | Type | Width | Description |
|------------|------|-------|-------------|
| `ID`* | Integer | 10 | Feature ID |
| `Name`* | String | 150 | Station name |
| `SeriesName`* | String | 80 | Timeseries identifier (FK to rainfall.csv SeriesName) |
| `Shape` | String | — | Point geometry as GeoJSON |

### 4.2 Rainfall Timeseries

**No geometry** — tabular | **GPKG tables:** `cat_timeseries` + `cat_timeseries_value`

| Field Name | Type | Width | Description |
|------------|------|-------|-------------|
| `SeriesName`* | String | 80 | Timeseries identifier (groups rows) |
| `Time`* | String | 20 | Time in `HH:MM` (RELATIVE) or `YYYY-MM-DD HH:MM` (ABSOLUTE) |
| `Value`* | Real | 12 | Rainfall intensity/volume |

### 4.3 Land Uses (Catalog)

**No geometry** — catalog table | **GPKG table:** `cat_landuses`

| Field Name | Type | Width | Description |
|------------|------|-------|-------------|
| `ID`* | String | 40 | Land use type identifier (e.g., `STREET`, `OPEN_SPACE`) |
| `Description` | String | 150 | Human-readable description |
| `Manning`* | Real | 10 | Manning's n roughness coefficient |

---

## Group 5: Pollution Sources

### 5.1 Discharge / Pollution Source Locations

**Geometry:** Point | **Source datasets:** discharge location CSVs

| Field Name | Type | Width | Description | 2022 CSV | 2023 CSV |
|------------|------|-------|-------------|----------|----------|
| `ID`* | Integer | 10 | Feature ID | stt | stt |
| `Name`* | String | 254 | Description/title | Title | Title |
| `Discharger` | String | 200 | Discharging entity | DonViXaThai | DonViXaThai |
| `Address` | String | 200 | Address | - | DiaChi |
| `Industry` | String | 100 | Industry sector | - | NganhNghe |
| `Receiver` | String | 150 | Receiving water body | - | NguonTiepNhan |
| `DischPt` | String | 200 | Discharge point description | - | ViTriXaThai |
| `IrrigSys` | String | 120 | Connected irrigation system | - | HTCTTL |
| `Treatment` | String | 200 | Wastewater treatment system | - | HTXLNT |
| `Permit` | String | 150 | Discharge permit reference | - | GPXT |
| `PermitOrg` | String | 100 | Permit-issuing authority | DonViCapGiayPhep | DonViCapPhep |
| `Standard` | String | 100 | Discharge quality standard | - | QuyChuanXT |
| `FlowRate` | String | 50 | Discharge flow rate | - | LLXT |
| `ExpiryDt` | String | 30 | Permit expiry date | - | NgayHetHan |
| `DischTerm` | String | 100 | Discharge period/term | - | ThoiHanXaThai |

---

## Component Summary

| Component | Geometry | CSV File | Group | Notes |
|-----------|----------|----------|-------|-------|
| Subcatchment | Polygon | (generated) | 1 | Not directly consumed by Delft3D conversion |
| River | LineString | `mang_luoi.../rivers.csv` | 2 | Open-channel branch |
| Canal/Ditch | LineString | `mang_luoi.../canals.csv` | 2 | Open-channel branch |
| Lake/Pond | Point | `mang_luoi.../lakes.csv` | 2 | StorageNode (area-form) |
| Mekong Dams | Point | (not converted) | 2 | Out of scope geographically |
| Sewer conduit | LineString | `thoat_nuoc/sewers.csv` | 3 | Closed-section branch |
| Manhole | Point | `thoat_nuoc/manholes.csv` | 3 | StorageNode + ObservationPoint |
| Pumping station | Point | `thoat_nuoc/pumps.csv` | 3 | Structure (Pump) + ObservationPoint |
| Weir/Culvert | Point | `thoat_nuoc/weir.csv` | 3 | Structure (Weir) |
| Orifice/Gate | Point | `thoat_nuoc/orifices.csv` | 3 | Structure (Orifice) |
| Outfall | Point | `thoat_nuoc/outfalls.csv` | 3 | Boundary condition + ObservationPoint |
| Hyetograph | Point | planning_map GPKG | 4 | Rainfall station (scenario module) |
| Rainfall TS | None | planning_map GPKG | 4 | Rainfall timeseries (scenario module) |
| Land Uses | None | planning_map GPKG | 4 | Manning n catalog for 2D mesh |
| Pollution source | Point | (not converted) | 5 | Water quality — out of scope |

---

## Notes

1. **Topology:** Rivers, canals, and sewers use `RouteShape` (GeoJSON LineString) for geometry,
   plus `FromNode`/`ToNode` for network connectivity (informational — not used programmatically
   by the Delft3D conversion; branch endpoints are derived from the RouteShape vertices).

2. **Cross-section type (`XSType`):** For sewers, `XSType` containing `'RECT'` (case-insensitive)
   or `Size_mm` in `WxH` / `W*H` notation triggers a rectangular closed cross-section.
   Otherwise a circular cross-section is used with `Diam_mm`.

3. **Field name truncation:** Shapefile DBF format limits field names to 10 characters.
   Longer names in this document are for readability; the actual shapefile field names may use
   abbreviated versions.

4. **Encoding:** HCMC datasets use `latin-1` encoding; Mekong datasets use `utf-8-sig`.
   The conversion reads CSVs with automatic encoding detection.

5. **Planning map (2D domain):** The `ground` and `roof` polygon layers in the planning-map
   GPKG file are the source for the 2D mesh domain, rain mask, and NWRW catchments.
   These are not CSV files but GeoPackage layers consumed by `domain2d.py` and `nwrw.py`.
