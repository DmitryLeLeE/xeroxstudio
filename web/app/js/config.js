// Сгенерировано из config.py и presets.py (tools/gen_config_js.py). Не править вручную.
export const CFG = {
 "APP_VERSION": "1.2.0",
 "CANVAS_FORMATS": {
  "2:3 Постер (1000×1500)": [
   1000,
   1500
  ],
  "1:1 Квадрат / Обложка (1200×1200)": [
   1200,
   1200
  ],
  "9:16 Stories / Обои (1080×1920)": [
   1080,
   1920
  ],
  "3:4 Принт (1200×1600)": [
   1200,
   1600
  ]
 },
 "RISO_PALETTES": {
  "Classic B&W (Xerox)": [
   [
    255,
    255,
    255
   ],
   [
    10,
    10,
    10
   ]
  ],
  "Vintage Newsprint (Cream / Charcoal)": [
   [
    244,
    238,
    224
   ],
   [
    22,
    22,
    24
   ]
  ],
  "Acid Cyberpunk (Neon Lime / Black)": [
   [
    214,
    255,
    0
   ],
   [
    10,
    10,
    10
   ]
  ],
  "Hot Pink Riot (Fluo Pink / Black)": [
   [
    255,
    42,
    133
   ],
   [
    12,
    12,
    12
   ]
  ],
  "Blueprint / Cyanotype (Navy / Cyan)": [
   [
    10,
    22,
    40
   ],
   [
    0,
    230,
    255
   ]
  ],
  "Crimson Zine (Off-White / Blood Red)": [
   [
    246,
    243,
    235
   ],
   [
    180,
    12,
    28
   ]
  ],
  "Toxic Violet (Lavender / Deep Violet)": [
   [
    230,
    220,
    245
   ],
   [
    35,
    10,
    60
   ]
  ],
  "Safety Orange (Blaze Orange / Charcoal)": [
   [
    255,
    87,
    34
   ],
   [
    18,
    18,
    18
   ]
  ],
  "Nightvision (Muted Green / Phosphor)": [
   [
    12,
    28,
    14
   ],
   [
    64,
    255,
    96
   ]
  ]
 },
 "CUSTOM_PALETTE": "Пользовательская (Custom)",
 "LAYOUTS": [
  [
   "Шахматка (зигзаг)",
   "staggered"
  ],
  [
   "Колонка (место под текст)",
   "column"
  ],
  [
   "Контактный лист (кадры)",
   "contact_sheet"
  ],
  [
   "Герой + копии",
   "center_hero"
  ],
  [
   "Колонка справа",
   "column_right"
  ],
  [
   "Диагональный каскад",
   "diagonal"
  ],
  [
   "Стопка (коллаж внахлёст)",
   "pile"
  ],
  [
   "Две колонки",
   "two_columns"
  ],
  [
   "Мозаика (большой + малые)",
   "mosaic"
  ],
  [
   "Диптих (два крупных)",
   "duo"
  ],
  [
   "Триптих (три полосы)",
   "triptych"
  ],
  [
   "Лента (ряд кадров)",
   "ribbon"
  ],
  [
   "Во весь лист",
   "full_page"
  ]
 ],
 "LAYOUT_ALIASES": {
  "reference_columns": "column"
 },
 "DITHERS": [
  [
   "Полутон (точки)",
   "halftone"
  ],
  [
   "Зерно Флойда–Стейнберга",
   "floyd"
  ],
  [
   "Трафарет (порог)",
   "stencil"
  ]
 ],
 "FIT_MODES": [
  [
   "Вписать целиком",
   "contain"
  ],
  [
   "Заполнить кадр",
   "cover"
  ]
 ],
 "TEXT_STYLES": [
  [
   "Белая плашка",
   "white_box"
  ],
  [
   "Чёрная лента (Dymo)",
   "dymo_tape"
  ],
  [
   "Контур (чёрный с белой обводкой)",
   "outline"
  ]
 ],
 "TEXT_ALIGNS": [
  [
   "По левому краю",
   "left"
  ],
  [
   "По центру",
   "center"
  ],
  [
   "По правому краю",
   "right"
  ]
 ],
 "FONTS": {
  "Arial Black": {
   "css": "\"Arial Black\", \"Rubik\", sans-serif",
   "weight": 900
  },
  "Arial Bold": {
   "css": "Arial, \"Rubik\", sans-serif",
   "weight": 700
  },
  "Impact": {
   "css": "Impact, \"Oswald\", sans-serif",
   "weight": 400
  },
  "Courier New Bold": {
   "css": "\"Courier New\", \"JetBrains Mono\", monospace",
   "weight": 700
  },
  "Consolas Bold": {
   "css": "Consolas, \"JetBrains Mono\", monospace",
   "weight": 700
  },
  "Times New Roman Bold": {
   "css": "\"Times New Roman\", \"PT Serif\", serif",
   "weight": 700
  }
 },
 "DEFAULT_STATE": {
  "format": "2:3 Постер (1000×1500)",
  "layout": "staggered",
  "rows": 4,
  "tilt": 0.0,
  "fit_mode": "contain",
  "bright": 1.3,
  "edge_x": 15,
  "edge_y": 10,
  "loss": 30,
  "censor": false,
  "sticker": false,
  "dither": "halftone",
  "dot_size": 7,
  "angle": 45,
  "contrast": 2.4,
  "noise": 25,
  "streaks": 15,
  "misreg": 3,
  "palette": "Classic B&W (Xerox)",
  "invert": false,
  "custom_colors": [
   [
    255,
    255,
    255
   ],
   [
    0,
    0,
    0
   ]
  ],
  "txt_top": "",
  "txt_bottom": "",
  "font": "Arial Black",
  "font_size": 34,
  "tstyle": "white_box",
  "text_align": "left",
  "txt_x": 7,
  "txt_y1": 10,
  "txt_y2": 70,
  "text_rot": 0.0,
  "copier_edge": 0,
  "paper": 0,
  "overprint": 0,
  "ink2": [
   255,
   60,
   140
  ],
  "tape": 0,
  "crop": [
   0.0,
   0.0,
   1.0,
   1.0
  ],
  "seed": 42,
  "img": null
 },
 "STYLE_KEYS": [
  "layout",
  "rows",
  "tilt",
  "fit_mode",
  "bright",
  "edge_x",
  "edge_y",
  "loss",
  "dither",
  "dot_size",
  "angle",
  "contrast",
  "noise",
  "streaks",
  "misreg",
  "copier_edge",
  "paper",
  "overprint",
  "ink2",
  "tape",
  "palette",
  "invert",
  "custom_colors",
  "font",
  "font_size",
  "tstyle",
  "text_align",
  "txt_x",
  "txt_y1",
  "txt_y2",
  "text_rot"
 ],
 "BUILTIN_PRESETS": {
  "Классический ксерокс": {
   "layout": "staggered",
   "rows": 4,
   "tilt": 0.0,
   "fit_mode": "contain",
   "bright": 1.3,
   "edge_x": 15,
   "edge_y": 10,
   "loss": 30,
   "dither": "halftone",
   "dot_size": 7,
   "angle": 45,
   "contrast": 2.4,
   "noise": 25,
   "streaks": 25,
   "misreg": 2,
   "copier_edge": 35,
   "paper": 0,
   "overprint": 0,
   "ink2": [
    255,
    60,
    140
   ],
   "tape": 0,
   "palette": "Classic B&W (Xerox)",
   "invert": false,
   "custom_colors": [
    [
     255,
     255,
     255
    ],
    [
     0,
     0,
     0
    ]
   ],
   "font": "Arial Black",
   "font_size": 34,
   "tstyle": "white_box",
   "text_align": "left",
   "txt_x": 7,
   "txt_y1": 10,
   "txt_y2": 70,
   "text_rot": 0.0
  },
  "Газетная печать": {
   "layout": "column",
   "rows": 5,
   "tilt": 0.0,
   "fit_mode": "contain",
   "bright": 1.3,
   "edge_x": 8,
   "edge_y": 6,
   "loss": 18,
   "dither": "halftone",
   "dot_size": 5,
   "angle": 15,
   "contrast": 1.8,
   "noise": 38,
   "streaks": 12,
   "misreg": 1,
   "copier_edge": 15,
   "paper": 0,
   "overprint": 0,
   "ink2": [
    255,
    60,
    140
   ],
   "tape": 0,
   "palette": "Vintage Newsprint (Cream / Charcoal)",
   "invert": false,
   "custom_colors": [
    [
     255,
     255,
     255
    ],
    [
     0,
     0,
     0
    ]
   ],
   "font": "Times New Roman Bold",
   "font_size": 34,
   "tstyle": "white_box",
   "text_align": "left",
   "txt_x": 7,
   "txt_y1": 10,
   "txt_y2": 70,
   "text_rot": 0.0
  },
  "Кислотный райот": {
   "layout": "staggered",
   "rows": 5,
   "tilt": 2.2,
   "fit_mode": "contain",
   "bright": 1.3,
   "edge_x": 15,
   "edge_y": 10,
   "loss": 45,
   "dither": "halftone",
   "dot_size": 9,
   "angle": 45,
   "contrast": 2.8,
   "noise": 20,
   "streaks": 30,
   "misreg": 5,
   "copier_edge": 0,
   "paper": 0,
   "overprint": 0,
   "ink2": [
    255,
    60,
    140
   ],
   "tape": 0,
   "palette": "Acid Cyberpunk (Neon Lime / Black)",
   "invert": false,
   "custom_colors": [
    [
     255,
     255,
     255
    ],
    [
     0,
     0,
     0
    ]
   ],
   "font": "Impact",
   "font_size": 44,
   "tstyle": "dymo_tape",
   "text_align": "left",
   "txt_x": 7,
   "txt_y1": 10,
   "txt_y2": 70,
   "text_rot": 0.0
  },
  "Панк-флаер": {
   "layout": "center_hero",
   "rows": 4,
   "tilt": 3.0,
   "fit_mode": "contain",
   "bright": 1.3,
   "edge_x": 22,
   "edge_y": 16,
   "loss": 55,
   "dither": "halftone",
   "dot_size": 11,
   "angle": 45,
   "contrast": 3.0,
   "noise": 30,
   "streaks": 35,
   "misreg": 6,
   "copier_edge": 0,
   "paper": 0,
   "overprint": 0,
   "ink2": [
    255,
    60,
    140
   ],
   "tape": 0,
   "palette": "Hot Pink Riot (Fluo Pink / Black)",
   "invert": false,
   "custom_colors": [
    [
     255,
     255,
     255
    ],
    [
     0,
     0,
     0
    ]
   ],
   "font": "Impact",
   "font_size": 52,
   "tstyle": "white_box",
   "text_align": "left",
   "txt_x": 7,
   "txt_y1": 10,
   "txt_y2": 70,
   "text_rot": 0.0
  },
  "Синька (cyanotype)": {
   "layout": "contact_sheet",
   "rows": 5,
   "tilt": 0.0,
   "fit_mode": "contain",
   "bright": 1.3,
   "edge_x": 15,
   "edge_y": 10,
   "loss": 22,
   "dither": "floyd",
   "dot_size": 6,
   "angle": 45,
   "contrast": 2.0,
   "noise": 14,
   "streaks": 10,
   "misreg": 1,
   "copier_edge": 0,
   "paper": 0,
   "overprint": 0,
   "ink2": [
    255,
    60,
    140
   ],
   "tape": 0,
   "palette": "Blueprint / Cyanotype (Navy / Cyan)",
   "invert": false,
   "custom_colors": [
    [
     255,
     255,
     255
    ],
    [
     0,
     0,
     0
    ]
   ],
   "font": "Courier New Bold",
   "font_size": 30,
   "tstyle": "dymo_tape",
   "text_align": "left",
   "txt_x": 7,
   "txt_y1": 10,
   "txt_y2": 70,
   "text_rot": 0.0
  },
  "Контактный лист 35 мм": {
   "layout": "contact_sheet",
   "rows": 6,
   "tilt": 0.0,
   "fit_mode": "contain",
   "bright": 1.3,
   "edge_x": 15,
   "edge_y": 10,
   "loss": 15,
   "dither": "halftone",
   "dot_size": 5,
   "angle": 45,
   "contrast": 2.2,
   "noise": 22,
   "streaks": 18,
   "misreg": 1,
   "copier_edge": 0,
   "paper": 0,
   "overprint": 0,
   "ink2": [
    255,
    60,
    140
   ],
   "tape": 0,
   "palette": "Classic B&W (Xerox)",
   "invert": false,
   "custom_colors": [
    [
     255,
     255,
     255
    ],
    [
     0,
     0,
     0
    ]
   ],
   "font": "Consolas Bold",
   "font_size": 28,
   "tstyle": "white_box",
   "text_align": "left",
   "txt_x": 7,
   "txt_y1": 10,
   "txt_y2": 70,
   "text_rot": 0.0
  },
  "Ризо-оверпринт": {
   "layout": "staggered",
   "rows": 4,
   "tilt": 1.2,
   "fit_mode": "contain",
   "bright": 1.3,
   "edge_x": 15,
   "edge_y": 10,
   "loss": 25,
   "dither": "halftone",
   "dot_size": 8,
   "angle": 30,
   "contrast": 2.2,
   "noise": 18,
   "streaks": 12,
   "misreg": 5,
   "copier_edge": 0,
   "paper": 55,
   "overprint": 70,
   "ink2": [
    255,
    60,
    140
   ],
   "tape": 0,
   "palette": "Пользовательская (Custom)",
   "invert": false,
   "custom_colors": [
    [
     244,
     238,
     224
    ],
    [
     25,
     55,
     170
    ]
   ],
   "font": "Impact",
   "font_size": 46,
   "tstyle": "white_box",
   "text_align": "left",
   "txt_x": 7,
   "txt_y1": 10,
   "txt_y2": 70,
   "text_rot": 0.0
  },
  "Склейка со скотчем": {
   "layout": "center_hero",
   "rows": 5,
   "tilt": 3.5,
   "fit_mode": "contain",
   "bright": 1.3,
   "edge_x": 20,
   "edge_y": 14,
   "loss": 28,
   "dither": "halftone",
   "dot_size": 6,
   "angle": 15,
   "contrast": 2.0,
   "noise": 34,
   "streaks": 20,
   "misreg": 2,
   "copier_edge": 0,
   "paper": 70,
   "overprint": 0,
   "ink2": [
    255,
    60,
    140
   ],
   "tape": 85,
   "palette": "Vintage Newsprint (Cream / Charcoal)",
   "invert": false,
   "custom_colors": [
    [
     255,
     255,
     255
    ],
    [
     0,
     0,
     0
    ]
   ],
   "font": "Courier New Bold",
   "font_size": 32,
   "tstyle": "dymo_tape",
   "text_align": "left",
   "txt_x": 7,
   "txt_y1": 10,
   "txt_y2": 70,
   "text_rot": 0.0
  },
  "Диагональ-панк": {
   "layout": "diagonal",
   "rows": 5,
   "tilt": 4.0,
   "fit_mode": "cover",
   "bright": 1.3,
   "edge_x": 18,
   "edge_y": 12,
   "loss": 50,
   "dither": "halftone",
   "dot_size": 9,
   "angle": 45,
   "contrast": 2.8,
   "noise": 28,
   "streaks": 30,
   "misreg": 5,
   "copier_edge": 0,
   "paper": 0,
   "overprint": 0,
   "ink2": [
    255,
    60,
    140
   ],
   "tape": 0,
   "palette": "Safety Orange (Blaze Orange / Charcoal)",
   "invert": false,
   "custom_colors": [
    [
     255,
     255,
     255
    ],
    [
     0,
     0,
     0
    ]
   ],
   "font": "Impact",
   "font_size": 48,
   "tstyle": "white_box",
   "text_align": "left",
   "txt_x": 7,
   "txt_y1": 10,
   "txt_y2": 70,
   "text_rot": 0.0
  },
  "Стопка снимков": {
   "layout": "pile",
   "rows": 5,
   "tilt": 6.0,
   "fit_mode": "cover",
   "bright": 1.3,
   "edge_x": 6,
   "edge_y": 5,
   "loss": 20,
   "dither": "halftone",
   "dot_size": 5,
   "angle": 15,
   "contrast": 1.9,
   "noise": 32,
   "streaks": 14,
   "misreg": 2,
   "copier_edge": 0,
   "paper": 65,
   "overprint": 0,
   "ink2": [
    255,
    60,
    140
   ],
   "tape": 60,
   "palette": "Vintage Newsprint (Cream / Charcoal)",
   "invert": false,
   "custom_colors": [
    [
     255,
     255,
     255
    ],
    [
     0,
     0,
     0
    ]
   ],
   "font": "Courier New Bold",
   "font_size": 30,
   "tstyle": "white_box",
   "text_align": "left",
   "txt_x": 7,
   "txt_y1": 10,
   "txt_y2": 70,
   "text_rot": 0.0
  },
  "Газетная мозаика": {
   "layout": "mosaic",
   "rows": 6,
   "tilt": 0.0,
   "fit_mode": "cover",
   "bright": 1.3,
   "edge_x": 6,
   "edge_y": 5,
   "loss": 18,
   "dither": "halftone",
   "dot_size": 5,
   "angle": 15,
   "contrast": 1.8,
   "noise": 36,
   "streaks": 10,
   "misreg": 1,
   "copier_edge": 20,
   "paper": 50,
   "overprint": 0,
   "ink2": [
    255,
    60,
    140
   ],
   "tape": 0,
   "palette": "Vintage Newsprint (Cream / Charcoal)",
   "invert": false,
   "custom_colors": [
    [
     255,
     255,
     255
    ],
    [
     0,
     0,
     0
    ]
   ],
   "font": "Times New Roman Bold",
   "font_size": 40,
   "tstyle": "white_box",
   "text_align": "left",
   "txt_x": 7,
   "txt_y1": 10,
   "txt_y2": 70,
   "text_rot": 0.0
  },
  "Триптих-синька": {
   "layout": "triptych",
   "rows": 4,
   "tilt": 0.0,
   "fit_mode": "cover",
   "bright": 1.3,
   "edge_x": 10,
   "edge_y": 8,
   "loss": 22,
   "dither": "floyd",
   "dot_size": 6,
   "angle": 45,
   "contrast": 2.1,
   "noise": 14,
   "streaks": 10,
   "misreg": 1,
   "copier_edge": 0,
   "paper": 0,
   "overprint": 0,
   "ink2": [
    255,
    60,
    140
   ],
   "tape": 0,
   "palette": "Blueprint / Cyanotype (Navy / Cyan)",
   "invert": false,
   "custom_colors": [
    [
     255,
     255,
     255
    ],
    [
     0,
     0,
     0
    ]
   ],
   "font": "Courier New Bold",
   "font_size": 30,
   "tstyle": "dymo_tape",
   "text_align": "left",
   "txt_x": 7,
   "txt_y1": 10,
   "txt_y2": 70,
   "text_rot": 0.0
  },
  "Постер во весь лист": {
   "layout": "full_page",
   "rows": 4,
   "tilt": 0.0,
   "fit_mode": "cover",
   "bright": 1.3,
   "edge_x": 14,
   "edge_y": 10,
   "loss": 0,
   "dither": "halftone",
   "dot_size": 9,
   "angle": 45,
   "contrast": 2.6,
   "noise": 24,
   "streaks": 28,
   "misreg": 3,
   "copier_edge": 45,
   "paper": 0,
   "overprint": 0,
   "ink2": [
    255,
    60,
    140
   ],
   "tape": 0,
   "palette": "Classic B&W (Xerox)",
   "invert": false,
   "custom_colors": [
    [
     255,
     255,
     255
    ],
    [
     0,
     0,
     0
    ]
   ],
   "font": "Impact",
   "font_size": 64,
   "tstyle": "outline",
   "text_align": "left",
   "txt_x": 7,
   "txt_y1": 10,
   "txt_y2": 70,
   "text_rot": 0.0
  },
  "Лента кинопроб": {
   "layout": "ribbon",
   "rows": 5,
   "tilt": 0.0,
   "fit_mode": "cover",
   "bright": 1.3,
   "edge_x": 15,
   "edge_y": 10,
   "loss": 35,
   "dither": "halftone",
   "dot_size": 7,
   "angle": 45,
   "contrast": 2.7,
   "noise": 22,
   "streaks": 26,
   "misreg": 4,
   "copier_edge": 0,
   "paper": 0,
   "overprint": 0,
   "ink2": [
    255,
    60,
    140
   ],
   "tape": 0,
   "palette": "Acid Cyberpunk (Neon Lime / Black)",
   "invert": false,
   "custom_colors": [
    [
     255,
     255,
     255
    ],
    [
     0,
     0,
     0
    ]
   ],
   "font": "Consolas Bold",
   "font_size": 34,
   "tstyle": "dymo_tape",
   "text_align": "left",
   "txt_x": 7,
   "txt_y1": 10,
   "txt_y2": 70,
   "text_rot": 0.0
  },
  "Ризо-диптих": {
   "layout": "duo",
   "rows": 4,
   "tilt": 0.0,
   "fit_mode": "cover",
   "bright": 1.3,
   "edge_x": 15,
   "edge_y": 10,
   "loss": 15,
   "dither": "halftone",
   "dot_size": 8,
   "angle": 30,
   "contrast": 2.2,
   "noise": 18,
   "streaks": 10,
   "misreg": 5,
   "copier_edge": 0,
   "paper": 55,
   "overprint": 75,
   "ink2": [
    255,
    60,
    140
   ],
   "tape": 0,
   "palette": "Пользовательская (Custom)",
   "invert": false,
   "custom_colors": [
    [
     244,
     238,
     224
    ],
    [
     25,
     55,
     170
    ]
   ],
   "font": "Impact",
   "font_size": 46,
   "tstyle": "white_box",
   "text_align": "left",
   "txt_x": 7,
   "txt_y1": 10,
   "txt_y2": 70,
   "text_rot": 0.0
  },
  "Ночное видение": {
   "layout": "center_hero",
   "rows": 5,
   "tilt": 0.0,
   "fit_mode": "contain",
   "bright": 1.3,
   "edge_x": 15,
   "edge_y": 10,
   "loss": 40,
   "dither": "halftone",
   "dot_size": 6,
   "angle": 45,
   "contrast": 2.6,
   "noise": 45,
   "streaks": 50,
   "misreg": 3,
   "copier_edge": 30,
   "paper": 0,
   "overprint": 0,
   "ink2": [
    255,
    60,
    140
   ],
   "tape": 0,
   "palette": "Nightvision (Muted Green / Phosphor)",
   "invert": false,
   "custom_colors": [
    [
     255,
     255,
     255
    ],
    [
     0,
     0,
     0
    ]
   ],
   "font": "Consolas Bold",
   "font_size": 32,
   "tstyle": "dymo_tape",
   "text_align": "left",
   "txt_x": 7,
   "txt_y1": 10,
   "txt_y2": 70,
   "text_rot": 0.0
  }
 },
 "MANIFESTOS": [
  {
   "lang": "en",
   "cat": "VISION",
   "top": "I SUFFER FROM THE CLARITY\nOF MY VISION",
   "bottom": "PROTECT ME FROM\nWHAT I CANNOT SEE"
  },
  {
   "lang": "en",
   "cat": "VISION",
   "top": "WHAT THE EYE SEES\nTHE MIND BELIEVES",
   "bottom": "FILTERED THROUGH LIES\nRECORDED IN DUST"
  },
  {
   "lang": "en",
   "cat": "VISION",
   "top": "EYES WIDE OPEN\nIN TOTAL DARKNESS",
   "bottom": "PAIN IS INEVITABLE\nCLARITY IS FATAL"
  },
  {
   "lang": "en",
   "cat": "VISION",
   "top": "THE OPTICAL NERVE\nREMEMBERS EVERYTHING",
   "bottom": "OVEREXPOSED\nUNDERSTOOD BY NONE"
  },
  {
   "lang": "en",
   "cat": "VISION",
   "top": "DON'T LOOK AT ME\nLOOK THROUGH ME",
   "bottom": "ALL SENSORS ACTIVE\nNO SIGNAL RECEIVED"
  },
  {
   "lang": "en",
   "cat": "VISION",
   "top": "RETINAL BURN-IN",
   "bottom": "PERMANENT RESIDUE"
  },
  {
   "lang": "en",
   "cat": "VISION",
   "top": "AN INVERTED SPECTRUM",
   "bottom": "WHERE SHADOWS EMIT LIGHT"
  },
  {
   "lang": "en",
   "cat": "SURVEILLANCE",
   "top": "CAPTURED IN HIGH RESOLUTION",
   "bottom": "ANONYMITY IS A LUXURY\nWE CANNOT AFFORD"
  },
  {
   "lang": "en",
   "cat": "SURVEILLANCE",
   "top": "SURVEILLANCE AS\nAN ACT OF LOVE",
   "bottom": "PRIVATE THOUGHTS\nBECOME PUBLIC SPECTACLE"
  },
  {
   "lang": "en",
   "cat": "SURVEILLANCE",
   "top": "WHO WATCHES\nTHE OBSERVER?",
   "bottom": "SILENT WITNESS\nGUILTY PARTNER"
  },
  {
   "lang": "en",
   "cat": "SURVEILLANCE",
   "top": "UNAUTHORIZED GAZE",
   "bottom": "PERCEPTION IS\nA HOSTILE ACT"
  },
  {
   "lang": "en",
   "cat": "SURVEILLANCE",
   "top": "FACIAL RECOGNITION FAILED",
   "bottom": "IDENTITY REJECTED"
  },
  {
   "lang": "en",
   "cat": "SURVEILLANCE",
   "top": "UNDER CONSTANT SCRUTINY",
   "bottom": "STILL UNRECOGNIZABLE"
  },
  {
   "lang": "en",
   "cat": "SURVEILLANCE",
   "top": "FEED ARCHIVED AT 04:00",
   "bottom": "INCIDENT NOT LOGGED"
  },
  {
   "lang": "en",
   "cat": "MEMORY",
   "top": "MEMORIES CORRUPTED\nBY FREQUENT REPLAY",
   "bottom": "DECAY OF REALITY\nREPLICATED IN TONER"
  },
  {
   "lang": "en",
   "cat": "MEMORY",
   "top": "REPEATED UNTIL\nMEANING DISSOLVES",
   "bottom": "A COPY OF A COPY\nOF A REAL LIFE"
  },
  {
   "lang": "en",
   "cat": "MEMORY",
   "top": "THE LAST IMAGE\nBEFORE REBOOT",
   "bottom": "WAS NEVER SAVED"
  },
  {
   "lang": "en",
   "cat": "MEMORY",
   "top": "DIGITAL GHOSTS\nIN ANALOG COPIES",
   "bottom": "A WITNESS TO\nOUR MUTUAL COLLAPSE"
  },
  {
   "lang": "en",
   "cat": "MEMORY",
   "top": "BUFFER OVERFLOW",
   "bottom": "DROWNING IN DETAILS"
  },
  {
   "lang": "en",
   "cat": "MEMORY",
   "top": "SYNTHETIC NOSTALGIA",
   "bottom": "FOR THINGS NEVER EXPERIENCED"
  },
  {
   "lang": "en",
   "cat": "BRUTAL",
   "top": "SYSTEM FAILURE\nIN ABSOLUTE SILENCE",
   "bottom": "DECODE WHAT REMAINS\nOF THE IMAGE"
  },
  {
   "lang": "en",
   "cat": "BRUTAL",
   "top": "THE FUTURE IS COLD\nAND HEAVILY RASTERIZED",
   "bottom": "NOTHING IS PERMANENT\nEXCEPT THE SCAN"
  },
  {
   "lang": "en",
   "cat": "BRUTAL",
   "top": "TONER RUNNING OUT",
   "bottom": "SO IS YOUR TIME"
  },
  {
   "lang": "en",
   "cat": "BRUTAL",
   "top": "A CRACK IN THE GLASS",
   "bottom": "A SHIFT IN REALITY"
  },
  {
   "lang": "en",
   "cat": "BRUTAL",
   "top": "MECHANICAL INDIFFERENCE",
   "bottom": "ORGANIC FAILURE"
  },
  {
   "lang": "en",
   "cat": "POST-PUNK",
   "top": "THE PANOPTICON CRUMBLES",
   "bottom": "UNDER ITS OWN WEIGHT"
  },
  {
   "lang": "en",
   "cat": "POST-PUNK",
   "top": "MONOCHROME REALITY",
   "bottom": "BLEEDING INTO GREY"
  },
  {
   "lang": "en",
   "cat": "POST-PUNK",
   "top": "STATIC ELECTROCUTION",
   "bottom": "ON COPIER GLASS"
  },
  {
   "lang": "en",
   "cat": "POST-PUNK",
   "top": "A GHOST IN THE COPIER",
   "bottom": "SPEAKING IN LINES"
  },
  {
   "lang": "en",
   "cat": "POST-PUNK",
   "top": "TERMINAL CLARITY",
   "bottom": "NO RETREAT POSSIBLE"
  },
  {
   "lang": "en",
   "cat": "COPIER",
   "top": "THE COPY IS WORSE\nTHAN THE ORIGINAL",
   "bottom": "AND THAT IS THE POINT"
  },
  {
   "lang": "en",
   "cat": "COPIER",
   "top": "PRESS START\nON THE GLASS",
   "bottom": "LET THE LIGHT\nDO THE ARGUING"
  },
  {
   "lang": "en",
   "cat": "COPIER",
   "top": "TONER RUNNING OUT",
   "bottom": "SO IS YOUR TIME"
  },
  {
   "lang": "en",
   "cat": "COPIER",
   "top": "EVERY GENERATION LOSES\nA LITTLE MORE TRUTH",
   "bottom": "AND GAINS A LITTLE MORE NOISE"
  },
  {
   "lang": "en",
   "cat": "COPIER",
   "top": "ONE ORIGINAL",
   "bottom": "ONE THOUSAND ACCOMPLICES"
  },
  {
   "lang": "en",
   "cat": "COPIER",
   "top": "FEED THE MACHINE\nA FACE",
   "bottom": "GET BACK A WARNING"
  },
  {
   "lang": "en",
   "cat": "COPIER",
   "top": "PAPER JAM\nIN THE ARCHIVE",
   "bottom": "REMOVE ALL OBSTRUCTIONS TO MEMORY"
  },
  {
   "lang": "en",
   "cat": "COPIER",
   "top": "50 COPIES FOR THE PRICE OF ONE",
   "bottom": "NOBODY OWNS THE LAST ONE"
  },
  {
   "lang": "en",
   "cat": "DIY",
   "top": "FOLD IT.\nCUT IT.",
   "bottom": "GIVE IT AWAY"
  },
  {
   "lang": "en",
   "cat": "DIY",
   "top": "MAKE IT BADLY\nMAKE IT TODAY",
   "bottom": "PERFECT IS NOT A DEADLINE"
  },
  {
   "lang": "en",
   "cat": "DIY",
   "top": "NO PERMISSION\nNO BUDGET",
   "bottom": "NO PROBLEM"
  },
  {
   "lang": "en",
   "cat": "DIY",
   "top": "A STAPLE IS A SPINE",
   "bottom": "A KITCHEN TABLE IS A PRESS"
  },
  {
   "lang": "en",
   "cat": "DIY",
   "top": "SCISSORS BEFORE SOFTWARE",
   "bottom": "GLUE BEFORE GENIUS"
  },
  {
   "lang": "en",
   "cat": "DIY",
   "top": "YOUR HANDS ARE\nTHE ONLY BRAND",
   "bottom": "WORTH TRUSTING"
  },
  {
   "lang": "en",
   "cat": "DIY",
   "top": "READ IT. COPY IT.",
   "bottom": "PASS IT ON"
  },
  {
   "lang": "en",
   "cat": "DIY",
   "top": "SMALL PRINT RUN\nHUGE INTENTIONS",
   "bottom": "LEAVE ONE ON THE BUS"
  },
  {
   "lang": "en",
   "cat": "CITY",
   "top": "THE WALLS ARE\nPAPER NOW",
   "bottom": "TEAR A STRIP\nAND READ"
  },
  {
   "lang": "en",
   "cat": "CITY",
   "top": "LAMPPOSTS FULL OF VOICES",
   "bottom": "NONE OF THEM ASKED"
  },
  {
   "lang": "en",
   "cat": "CITY",
   "top": "3 A.M.\nTHE PHOTOCOPIER STILL WARM",
   "bottom": "THE STREETS ALREADY SPEAKING"
  },
  {
   "lang": "en",
   "cat": "CITY",
   "top": "CONCRETE REMEMBERS\nEVERY POSTER",
   "bottom": "UNDER EVERY LAYER OF PASTE"
  },
  {
   "lang": "en",
   "cat": "CITY",
   "top": "WHAT YOU PASTE TODAY",
   "bottom": "THE RAIN WILL EDIT TOMORROW"
  },
  {
   "lang": "en",
   "cat": "CITY",
   "top": "THIS BUS STOP\nIS A GALLERY",
   "bottom": "ADMISSION IS ATTENTION"
  },
  {
   "lang": "en",
   "cat": "CITY",
   "top": "NOISE IS A\nPUBLIC LANGUAGE",
   "bottom": "SPEAK IT LOUDLY"
  },
  {
   "lang": "en",
   "cat": "CITY",
   "top": "FLYER FOR A\nPARTY THAT NEVER HAPPENED",
   "bottom": "EVERYONE CAME"
  }
 ]
};
