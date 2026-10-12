# Power BI build guide

Step-by-step instructions to build the report from the star-schema CSVs in `data/processed/`.
Budget about 4–6 hours the first time. Building it yourself is the point: interviewers will ask *how* you did each part.

**You need:** Power BI Desktop (free, Windows only, from the Microsoft Store). On a Mac, use a Windows virtual machine or a Windows PC.

---

## Step 1 · Set the import locale (do this first)

The CSVs use a dot as the decimal separator (`58.90`). If your Windows or Power BI language is German, French, Portuguese and so on,
Power BI may read `58.90` as `5890` and every money value will be wrong.

1. **File > Options and settings > Options**
2. Under **CURRENT FILE > Regional Settings**, set **Locale for import** to **English (United States)**.

## Step 2 · Load the data

Load these 7 files from `data/processed/` with **Home > Get data > Text/CSV**, one at a time, and click **Load**:

`FactOrderItems.csv`, `FactOrders.csv`, `FactLateRiskScores.csv`, `DimDate.csv`, `DimCustomer.csv`, `DimProduct.csv`, `DimSeller.csv`

Then open **Home > Transform data** (Power Query) and check the column types:

| Columns | Type |
|---|---|
| All `...Key` columns, `OrderItemNumber`, counts, flags (`Is...`), `ReviewScore`, `PromisedDays`, `DelayDays`, `RiskDecile`, `...Sort` | Whole number |
| `Price`, `Freight`, `ProductValue`, `FreightValue`, `PaymentValue` | Fixed decimal number (currency) |
| `DistanceKm`, `DeliveryDays`, `TotalWeightG`, `LateRiskScore`, `PredictedDeliveryDays`, `WeightG`, `VolumeCm3` | Decimal number |
| `OrderDate`, `DeliveredDate`, `EstimatedDate`, `Date`, `MonthStart`, `WeekStart`, `FirstOrderDate` | Date |
| `ZipPrefix` (customer and seller) | **Text** (keeps the leading zero) |

**Close & Apply.**

> *Optional Power Query skill to show:* create a parameter `DataFolder` (**Manage Parameters > New**) holding the folder path,
> and edit each query's `Source` step to use `DataFolder & "FactOrders.csv"`. The report then works on any machine by changing one value.

## Step 3 · Build the relationships

Go to **Model view**. Power BI may have auto-detected some relationships; open **Home > Manage relationships**, delete them all,
and create these (all *Many to one*, *Single* cross-filter direction):

| From (many) | To (one) | Active |
|---|---|---|
| `FactOrderItems[OrderDate]` | `DimDate[Date]` | ✔ |
| `FactOrderItems[CustomerKey]` | `DimCustomer[CustomerKey]` | ✔ |
| `FactOrderItems[ProductKey]` | `DimProduct[ProductKey]` | ✔ |
| `FactOrderItems[SellerKey]` | `DimSeller[SellerKey]` | ✔ |
| `FactOrders[OrderDate]` | `DimDate[Date]` | ✔ |
| `FactOrders[DeliveredDate]` | `DimDate[Date]` | **✘ inactive** (Power BI makes it inactive automatically) |
| `FactOrders[CustomerKey]` | `DimCustomer[CustomerKey]` | ✔ |
| `FactOrders[SellerKey]` | `DimSeller[SellerKey]` | ✔ |
| `FactLateRiskScores[OrderDate]` | `DimDate[Date]` | ✔ |
| `FactLateRiskScores[CustomerKey]` | `DimCustomer[CustomerKey]` | ✔ |
| `FactLateRiskScores[SellerKey]` | `DimSeller[SellerKey]` | ✔ |

Arrange the model view as a star: facts in the middle, dimensions around them. **Take a screenshot for your README.**

Why no bidirectional relationships: see [`docs/data_model.md`](../docs/data_model.md).

## Step 4 · Model settings

1. **Mark the date table:** select `DimDate` > **Table tools > Mark as date table** > choose `Date`.
2. **Sort by column** (select the column > **Column tools > Sort by column**):
   - `DimDate[Month]` by `MonthNumber`
   - `DimDate[DayOfWeek]` by `DayOfWeekNumber`
   - `FactOrders[DelayBucket]` by `DelayBucketSort`
   - `FactLateRiskScores[RiskBand]` by `RiskBandSort`
3. **Data categories** (for maps): `DimCustomer[State]` and `DimSeller[State]` = *State or Province*; `City` columns = *City*.
4. **Hide technical columns** from report view (right-click > *Hide in report view*): every `...Key` column in the fact tables,
   `OrderItemNumber`, `...Sort` columns, `CustomerUniqueID`, `ProductID`, `SellerID`.
5. Set **Summarize by = None** for `ReviewScore`, `PromisedDays`, `PurchaseHour`, `Year`, `MonthNumber`.

## Step 5 · Add the measures

1. **Home > Enter data**, name the table `_Measures`, click **Load**.
2. Open **DAX query view** (the fourth icon in the left bar), paste the whole of [`measures_query_view.dax`](measures_query_view.dax).
3. Click **Run**: you get three result tables. Compare them with the expected values in step 6.
4. Click **Update model with changes**: all 61 measures are added to `_Measures`.
   *If your Power BI version doesn't show this button, update Power BI Desktop, or create each measure manually from [`measures.dax`](measures.dax) (right-click `_Measures` > New measure).*
5. Delete the empty `Column1` in `_Measures`. The table moves to the top of the Data pane with a calculator icon.
6. Set **format strings** (Measure tools > Format, or the Properties pane) as listed in [`measures.dax`](measures.dax) or [`docs/kpi_dictionary.md`](../docs/kpi_dictionary.md).
   *Faster:* in Model view, multi-select all percentage measures and set the format once.
7. Optional but recommended: set **Display folder** for each measure (Model view > Properties) using the folder names in `measures.dax` (`1 Sales`, `2 Time intelligence`, ...).

## Step 6 · Validate the numbers

Your measures must match the values computed independently in Python (`notebooks/01_eda_and_kpis.ipynb`). If one doesn't, check relationships, data types and the import locale.

| Measure | All data (Jan 2017 - Aug 2018) | Jan-Aug 2017 | Jan-Aug 2018 | Change |
|---|---:|---:|---:|---:|
| Revenue | R$ 13,449,530 | R$ 3,080,851 | R$ 7,341,037 | +138.3% |
| Freight Revenue | R$ 2,238,867 | R$ 494,224 | R$ 1,254,634 | +153.9% |
| GMV | R$ 15,688,397 | R$ 3,575,075 | R$ 8,595,671 | +140.4% |
| Orders | 97,905 | 22,562 | 53,530 | +137.3% |
| Items Sold | 111,752 | 25,576 | 61,135 | +139.0% |
| Avg Order Value | R$ 137.37 | R$ 136.55 | R$ 137.14 | +0.4% |
| Items per Order | 1.14 | 1.13 | 1.14 | +0.01 |
| Freight % of Revenue | 16.6% | 16.0% | 17.1% | +1.0 pp |
| Active Customers | 94,703 | 21,936 | 52,336 | +138.6% |
| Active Sellers | 3,029 | 1,212 | 2,354 | +94.2% |
| Repeat Customer Rate | 3.0% | 2.6% | 2.1% | -0.5 pp |
| Cancellation Rate | 1.2% | 1.8% | 0.9% | -0.9 pp |
| Delivered Orders | 96,203 | 21,997 | 52,777 | +139.9% |
| Late Delivery Rate | 6.8% | 3.5% | 7.7% | +4.2 pp |
| On-Time Delivery Rate | 93.2% | 96.5% | 92.3% | -4.2 pp |
| Avg Delivery Days | 12.54 | 12.18 | 12.14 | -0.05 |
| Avg Review Score | 4.089 | 4.136 | 4.090 | -0.05 |
| Bad Review Rate | 14.6% | 13.2% | 14.8% | +1.6 pp |
| Top 10% Sellers Revenue Share | 67.4% | 62.7% | 63.7% | +1.0 pp |

Risk bands (test period, Jun–Aug 2018):

| Risk band | Scored Orders | Actual Late Rate | Share of Late Orders Caught |
|---|---:|---:|---:|
| High | 1,861 | 12.7% | 35.1% |
| Medium | 3,720 | 5.0% | 27.5% |
| Low | 13,022 | 1.9% | 37.4% |

> Being able to say *"I validated my core DAX measures against an independent Python calculation"* is a strong interview line.

## Step 7 · Apply the theme

**View > Themes > Browse for themes** > select [`olist_theme.json`](olist_theme.json). It sets a colour-blind-safe palette and consistent fonts.
Set the canvas to 16:9 (**View > Page view > Fit to page**; **Format page > Canvas settings**: 1280 × 720).

## Step 8 · Build the report pages

Layout rule for every page: title and slicers in a band at the top, KPI cards in one row, two to four charts below.
Leave white space; align everything (**Format > Align**). Never use a chart with two Y-axes: plot measures with different units in separate charts.

### Page 1 · Executive overview

| Visual | Fields | Notes |
|---|---|---|
| Slicers | `DimDate[Year]`, `DimCustomer[Region]` | Tile or dropdown style |
| 6 Cards | `Revenue`, `Orders`, `Avg Order Value`, `Active Customers`, `On-Time Delivery Rate`, `Avg Review Score` | For the revenue card: *Format > General > Title > Subtitle*, click **fx**, Field value = `Revenue YoY Label` |
| Clustered column chart | X: `DimDate[YearMonth]`, Y: `Revenue` | Title: "Monthly revenue". Black Friday (Nov 2017) stands out |
| Line chart | X: `DimDate[YearMonth]`, Y: `Late Delivery Rate` | Title: "Late delivery rate". Separate chart, **not** a second axis |
| Bar chart | Y: `DimProduct[Category]`, X: `Revenue` | Filters pane > Top N = 10 by `Revenue` |
| Filled map or bar chart | `DimCustomer[State]`, `Revenue` | Bar chart is easier to read; map looks nicer in a portfolio |

Dynamic page title: a card or text box using `Selected Period`, e.g. "Executive overview · Jan 2017 - Aug 2018".

### Page 2 · Delivery and satisfaction (the key story)

| Visual | Fields | Notes |
|---|---|---|
| 4 Cards | `Late Delivery Rate`, `Avg Delivery Days`, `Avg Days vs Estimate`, `Review Gap On Time vs Late` | |
| Column chart | X: `FactOrders[DelayBucket]`, Y: `Avg Review Score` | **The headline chart.** Filter out "Not delivered". Sort by the axis (uses `DelayBucketSort`) |
| Bar chart | Y: `DimCustomer[State]`, X: `Late Delivery Rate` | *Format > Bars > Colors > fx > Field value = `Late Rate Color`* (green/amber/red) |
| Line chart | X: `DimDate[YearMonth]`, Y: `Avg Promised Days` and `Avg Delivery Days` | Same unit (days), so one axis is fine. Shows the promise being cut in mid-2018 |
| Matrix | Rows: `DimCustomer[Region]`, Columns: `DimDate[Year]`, Values: `Late Delivery Rate`, `Avg Review Score` | Conditional formatting: background colour scale |

### Page 3 · Customers and sellers

| Visual | Fields | Notes |
|---|---|---|
| 5 Cards | `Active Customers`, `New Customers`, `Repeat Customer Rate`, `Active Sellers`, `Top 10% Sellers Revenue Share` | |
| Table: seller scorecard | `DimSeller[SellerName]`, `DimSeller[State]`, `Seller Revenue Rank`, `Revenue`, `Orders`, `Late Delivery Rate`, `Avg Review Score` | Top N = 20 by `Revenue`. Data bars on `Revenue`, background colour on `Late Delivery Rate` |
| Table: categories | `DimProduct[Category]`, `Revenue`, `Late Delivery Rate (Product View)`, `Bad Review Rate (Product View)` | The *Product View* measures use `TREATAS` (be ready to explain) |
| Donut or bar chart | `FactOrders[PaymentType]`, `All Orders` | |
| Column chart | X: `DimDate[YearMonth]`, Y: `New Customers` | |

### Page 4 · Delivery risk model

| Visual | Fields | Notes |
|---|---|---|
| Text box | Model summary | "Two-stage model: predicts delivery time, compares it with the promise. Test ROC-AUC 0.74. Flagging the riskiest 10% of orders catches 35% of late orders." |
| 3 Cards | `Scored Orders`, `Actual Late Rate (Scored)`, `Share of Late Orders Caught` | Add a visual-level filter `RiskBand = High` to the last card |
| Column chart | X: `FactLateRiskScores[RiskBand]`, Y: `Actual Late Rate (Scored)` | High 12.7% vs Low 1.9% |
| Line chart (gains curve) | X: `FactLateRiskScores[RiskDecile]`, Y: `Cumulative Late Orders Caught` | Set the X axis type to *Categorical* |
| Table | `DimSeller[SellerName]`, `Scored Orders`, `Actual Late Rate (Scored)` | Filter `RiskBand = High`: which sellers have most high-risk orders |

### Page 5 · Seller detail (drill-through)

1. New page, add `DimSeller[SellerName]` to the **Drill through** well in the Visualizations pane.
2. Add cards (`Revenue`, `Orders`, `Late Delivery Rate`, `Avg Review Score`), a monthly revenue column chart and a review-score-by-`DelayBucket` chart.
3. On page 3, right-click a seller in the scorecard > **Drill through > Seller detail**.

## Step 9 · Polish (what makes it look professional)

- [ ] Page navigation: **Insert > Buttons > Navigator > Page navigator** at the top of each page
- [ ] A **Reset filters** button: **View > Bookmarks**, add a bookmark with no filters, link a button to it
- [ ] Tooltips: create a small *tooltip page* (Page information > Allow use as tooltip) with `Avg Review Score` and `Late Delivery Rate`, and assign it to the monthly charts
- [ ] Every visual has a clear title that states what it shows; axis titles removed where obvious
- [ ] Consistent number formats (R$ without decimals for totals, % with one decimal)
- [ ] Check speed with **Optimize > Performance analyzer**: every visual should render in well under a second
- [ ] Save as `powerbi/Olist_KPI_Report.pbix`

## Step 10 · Share it

- **Screenshots:** export each page (**File > Export > Export to PDF**, or screenshots) into `images/` and reference them in the README. Recruiters look at images first.
- **The .pbix file:** commit it to the repository (it should be well under GitHub's 100 MB limit).
- **Live link:** *Publish to web* needs a work or school Microsoft account; personal Gmail/Outlook accounts can't sign up for the Power BI service. If you don't have one, a 2-minute screen recording (e.g. Loom) linked from the README works just as well.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Revenue is 10x or 100x too large | Decimal separator read with the wrong locale | Step 1, then reload |
| YoY / PY measures are blank | Date table not marked, or relationship missing | Step 4.1 and step 3 |
| A measure gives the same value for every category | That dimension doesn't filter the table the measure reads | Use the `(Product View)` pattern or check the relationship |
| Months sorted alphabetically (Apr, Aug, Dec...) | Sort by column not set | Step 4.2, or use `YearMonth` |
| Zip codes lost the leading zero | Column typed as number | Set `ZipPrefix` to Text in Power Query |
