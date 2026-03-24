PROJECT = {
    "name": "Логистический хаб Подмосковье",
    "type": "Складская недвижимость класса А",
    "area_sqm": 50000,
    "investment_bln": 3.5,
    "horizon_years": 10,
    "discount_rate": 0.12,
    "rent_rate_sqm_year": 6500,
    "occupancy_rate": 0.95,
    "opex_pct": 0.15,
    "capex_reserve_pct": 0.02,
    "terminal_cap_rate": 0.10,
    "construction_cost_sqm": 55000,

    # Market benchmarks for verification
    "market_rent_range": (6000, 7200),
    "market_occupancy_range": (0.88, 0.92),
    "market_construction_cost_range": (58000, 65000),

    # Pre-calculated results (deterministic)
    "npv": 1.2,  # млрд руб
    "irr": 0.185,
    "payback_years": 5.8,

    # Red flags
    "flags": [
        {
            "parameter": "Заполняемость",
            "project_value": "95%",
            "market_range": "88-92%",
            "severity": "high",
            "comment": "Предпосылка агрессивная. Рыночная заполняемость складов класса А в Московском регионе составляет 88-92%. Заполняемость 95% возможна только для объектов с long-term якорным арендатором.",
        },
        {
            "parameter": "Стоимость строительства",
            "project_value": "55 000 руб/кв.м",
            "market_range": "58 000-65 000 руб/кв.м",
            "severity": "medium",
            "comment": "Стоимость строительства ниже рыночного диапазона. Возможно не учтены инфраструктурные затраты (подъездные пути, инженерные сети) или стоимость земельного участка.",
        },
        {
            "parameter": "Ставка аренды",
            "project_value": "6 500 руб/кв.м/год",
            "market_range": "6 000-7 200 руб/кв.м/год",
            "severity": "ok",
            "comment": "Ставка аренды находится в рамках рыночного диапазона. Предпосылка обоснована.",
        },
    ],

    # Sensitivity table data
    "sensitivity": {
        "occupancy_rates": [0.85, 0.88, 0.90, 0.92, 0.95],
        "rent_rates": [5500, 6000, 6500, 7000, 7500],
        "npv_matrix": [
            [-0.2, 0.1, 0.4, 0.7, 1.2],
            [0.0, 0.3, 0.6, 0.9, 1.4],
            [0.2, 0.5, 0.8, 1.2, 1.7],
            [0.4, 0.8, 1.1, 1.4, 2.0],
            [0.7, 1.0, 1.3, 1.7, 2.3],
        ],
    },

    # Cash flows for NPV/IRR calculation
    "cash_flows": [
        -3500.0,  # Year 0
        256.0,    # Year 1
        268.0,    # Year 2
        280.0,    # Year 3
        293.0,    # Year 4
        306.0,    # Year 5
        320.0,    # Year 6
        335.0,    # Year 7
        350.0,    # Year 8
        366.0,    # Year 9
        2883.0,   # Year 10 (operating + terminal value)
    ],
}
