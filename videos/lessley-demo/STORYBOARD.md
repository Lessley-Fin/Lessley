---
format: 1920x1080
duration: 315s
message: "Lessley תופסת עבורכם את החיסכון שכבר הרווחתם — אוטומטית, בכל רכישה"
arc: הבטחה → הכאב → ההצטרפות → הכלים → ההוכחה → הביטחון → הסגירה
audience: "מציגים את המוצר — בעלי עניין, שופטים, לקוחות פוטנציאליים"
mode: collaborative
---

## Frame 1 — ההבטחה

- scene: הלוגו נבנה על רקע נייבי, האייפון נכנס מלמטה ונוחת — הנשא של כל הסרט
- duration: 15s
- transition_in: cut
- status: built
- blueprint: logo-assemble-lockup
- rules: waterfall-entry, spring-pop-entrance
- voiceover: "כל חודש אתם קונים באותן חנויות — ומפספסים הנחות שכבר מגיעות לכם. Lessley היא הטייס האוטומטי הפיננסי שסוגר את הפער הזה."
- src: compositions/frames/01-open.html

פתיחה קרה על ההבטחה, לא על המוצר. הלוגו מתלכד, ומיד אחריו האייפון עולה מלמטה ונוחת
במקומו — הצופה רואה את הנשא נולד. **יציאה: Z קדימה** (דחיפה פנימה אל המסך).

## Frame 2 — הכאב

- scene: כרטיסי אשראי, קבלות ולוגואים של מועדונים נערמים סביב הצופה עד לחנק; המונה "₪0 נחסך" קפוא במרכז
- duration: 20s
- transition_in: zoom-through
- status: built
- blueprint: overwhelm-surround
- rules: depth-scatter-assemble, counting-dynamic-scale
- voiceover: "יש לכם מועדוני נאמנות, כרטיסי אשראי עם הטבות וקופונים שמתחלפים כל יום. אף אחד לא מצליח לעקוב אחרי הכול בזמן אמת. Lessley עושה את זה בשבילכם — אוטומטית."
- src: compositions/frames/02-problem.html

הסצנה היחידה בלי טלפון. ההצטברות סוגרת על המרכז, ואז המונה הקפוא נשבר — והטלפון
נכנס לתוך החלל שנפתח. זה מה שמצדיק את כל מה שבא אחריו.

## Frame 3 — הרשמה · חשבון

- scene: מסך יצירת החשבון; סמן נוגע בכל שדה והטקסט נכתב תו-תו
- duration: 12s
- transition_in: cut
- status: built
- blueprint: cursor-ui-demo
- rules: discrete-text-sequence, cursor-click-ripple
- voiceover: "ההרשמה מתחילה בפרטים בסיסיים. שימו לב — בשלב הזה עדיין לא נוצר חשבון. השם והאימייל רק נשמרים בצד, עד שתאמתו אותם."
- src: compositions/frames/03-signup-account.html

מד ההתקדמות בן 5 השלבים נדלק כאן ונשאר על המסך עד פריים 7. ההערה על "עדיין לא נוצר
חשבון" היא פרט אמיתי מהקוד — היא מה שהופך את הסצנה להסבר ולא לצילום מסך.

## Frame 4 — הרשמה · אימות אימייל

- scene: מסך "בדקו את תיבת הדואר"; שש ספרות נוחתות בתאים אחת-אחת, הטיימר סופר לאחור
- duration: 11s
- transition_in: cut
- status: built
- blueprint: device-surface-showcase
- rules: spring-pop-entrance, svg-path-draw
- voiceover: "נשלח לכם קוד בן שש ספרות. רק אחרי אימות מוצלח החשבון באמת נוצר — כך אין חשבונות רפאים במערכת."
- src: compositions/frames/04-signup-verify.html

הספרה השישית נוחתת → וי ירוק נמשך (`svg-path-draw`) → מעבר. האימות עצמו הוא הקצב.

## Frame 5 — הרשמה · בחירת מועדונים

- scene: רשת לוגואים של מועדונים; ארבעה נבחרים בזה אחר זה, המונה "נבחר" עולה
- duration: 16s
- transition_in: cut
- status: built
- blueprint: grid-card-assemble
- rules: cursor-click-ripple, counting-dynamic-scale
- voiceover: "עכשיו מסמנים באילו מועדונים אתם כבר חברים. זה מה שמאפשר ל-Lessley להתאים לכם דילים כבר מהרגע הראשון, עוד לפני שהיא ראתה עסקה אחת. חייבים לבחור לפחות מועדון אחד."
- src: compositions/frames/05-signup-clubs.html

ארבעת המועדונים שנבחרים כאן הם אותם ארבעה שיחזרו בכל שאר הסרט (`demo-data.js`).
עקביות הדאטה היא מה שגורם לדמו להיראות כמו משתמש אחד אמיתי.

## Frame 6 — הרשמה · רמת התאמה

- scene: שלוש האפשרויות; הבחירה זזה בין רחב/בינוני/מחמיר ותצוגה מקדימה של הדילים מסתננת בזמן אמת
- duration: 16s
- transition_in: cut
- status: built
- blueprint: panel-edit-live-sync
- rules: control-target-sync, stat-bars-and-fills
- voiceover: "כאן אתם קובעים כמה מחמיר הסינון. 'רחב' מציג את שבעים וחמישה האחוזים המתאימים ביותר — יותר דילים, כולל פחות רלוונטיים. 'בינוני' — חמישים אחוז, איזון. 'מחמיר' — רק עשרים וחמישה האחוזים שהכי מתאימים להרגלי ההוצאה שלכם."
- src: compositions/frames/06-signup-match.html

`control-target-sync` הוא הלב: הבחירה והתוצאה משתנות באותו ביט. הצופה לא צריך שיסבירו
לו מה רמת ההתאמה עושה — הוא רואה את זה קורה.

## Frame 7 — הרשמה · בנקאות פתוחה

- scene: מסך החיבור; שלוש נקודות הערך עולות, ואז תג "לקריאה בלבד" ננעל על מנעול
- duration: 15s
- transition_in: cut
- status: built
- blueprint: titlecard-reveal
- rules: waterfall-entry, svg-icon-enrichment
- voiceover: "השלב האחרון הוא החיבור שפותח את הכוח האמיתי: בנקאות פתוחה. Lessley קוראת את העסקאות שכבר ביצעתם — לקריאה בלבד — כדי לראות איפה אתם באמת קונים. היא לא יכולה להזיז את הכסף שלכם, ואף פעם לא שומרת את סיסמאות הבנק."
- src: compositions/frames/07-signup-banking.html

הסצנה השקטה של המערכה הראשונה. אחרי חמישה מסכים של פעולה, כאן עוצרים — כי זו הנקודה
שבה נדרש אמון. **יציאה: מעלה** (מסקנה מתרוממת).

## Frame 8 — התחברות

- scene: מסך ההתחברות; מעבר בין "סיסמה" ל"קוד באימייל", ורמז למסלול איפוס הסיסמה
- duration: 15s
- transition_in: cut
- status: built
- blueprint: cursor-ui-demo
- rules: theme-crossfade-morph, cursor-click-ripple
- voiceover: "בכניסות הבאות יש שתי דרכים: סיסמה רגילה, או קוד חד-פעמי למייל — בלי סיסמה בכלל. ואם שכחתם — מסלול איפוס מלא: מייל, קוד, סיסמה חדשה."
- src: compositions/frames/08-login.html

`theme-crossfade-morph` מחליף את גוף הטופס תחת עוגן קבוע (הכותרת "ברוכים השבים"),
כך שהמעבר בין שני מצבי ההתחברות קורא כהחלפה ולא כמסך חדש.

## Frame 9 — מפת האפליקציה

- scene: הטלפון נסוג, ארבעת המסכים הראשיים נפרשים כתחנות; מצלמה עוברת ביניהן וחוזרת לטלפון
- duration: 15s
- transition_in: inverse-zoom
- status: built
- blueprint: spatial-pan-stations
- rules: viewport-change, waterfall-entry
- voiceover: "האפליקציה בנויה מארבעה מסכים ראשיים בסרגל התחתון: אופטימיזציה, תובנות, חם והמלצות. למעלה — פעמון ההתראות עם חיווי אדום כשיש חדשות, ולידו האווטאר שמוביל לפרופיל ולהגדרות."
- src: compositions/frames/09-nav-map.html

**נקודת ציר של הסרט.** היחידה שבה עוזבים את מסגרת הטלפון היחידה ורואים את כל השטח.
ה-inverse-zoom בכניסה הוא הגעה — משהו גדול יותר נוחת.

## Frame 10 — אופטימיזציה · הקלט

- scene: בחירת חנות, הקלדת ₪412, בורר מקסימום דילים; לחיצה על "מציאת המחירים הטובים ביותר" ומצב עיבוד
- duration: 15s
- transition_in: cut
- status: built
- blueprint: prompt-type-submit-generate
- rules: discrete-text-sequence, press-release-spring
- voiceover: "זה הלב של Lessley. בוחרים חנות — או מחפשים בכל השוק — מזינים את סכום העגלה, ומגדירים כמה דילים מותר לשלב יחד. המנוע בודק את כל הצירופים האפשריים ומחזיר את השילוב החוקי והזול ביותר."
- src: compositions/frames/10-optimizer-input.html

**הטלפון זז למרכז האמיתי** (`nudge-curve`, שמור ל-3 פעמים בסרט). מכאן ועד פריים 12 זו
פסקה אחת רצופה — ההרצה של המנוע.

## Frame 11 — אופטימיזציה · השילוב המנצח

- scene: כרטיס "השילוב הטוב ביותר"; ₪412 יורד ל-₪317 בספירה חיה, תג החיסכון קופץ בזהב
- duration: 12s
- transition_in: cut
- status: built
- blueprint: dataviz-countup
- rules: counting-dynamic-scale, spring-pop-entrance
- voiceover: "התוצאה מציגה כמה שילמתם, כמה תשלמו עכשיו, וכמה חסכתם — באחוזים ובשקלים."
- src: compositions/frames/11-optimizer-stack.html

**הפעם הראשונה שהזהב מופיע.** זוהי נקודת התשלום של כל ההבטחה מפריים 1 — הזוהר הטילי
ברקע מתחזק בדיוק על הביט הזה. שקט לפני, פיצוץ עליו.

## Frame 12 — אופטימיזציה · איך זה מצטבר

- scene: האקורדיון "איך זה מצטבר" נפתח; שלבי החישוב יורדים אחד-אחד עם היתרה שמתעדכנת
- duration: 13s
- transition_in: cut
- status: built
- blueprint: transcript-scroll-artifact-reveal
- rules: anchored-layout-expand, coordinate-target-zoom
- voiceover: "ופה השקיפות המלאה: 'איך זה מצטבר' פורס את החישוב צעד-צעד — איזו הנחה חלה על מה, כמה נשאר לתשלום אחרי כל שלב, ומאיזה מועדון או כרטיס כל הטבה הגיעה. מתחת — 'אפשרויות נוספות' עם השילובים המדורגים הבאים."
- src: compositions/frames/12-optimizer-steps.html

השקיפות היא הטיעון. `coordinate-target-zoom` מקרב לאזור השלבים כדי שהמספרים יהיו
קריאים — הפעם היחידה שנכנסים לתוך המסך.

## Frame 13 — חיפוש דילים

- scene: מסננים נבחרים, תוצאות נשפכות לרשימה, כרטיס נפתח לתנאי ההטבה וקוד הקופון מועתק
- duration: 17s
- transition_in: cut
- status: built
- blueprint: cursor-ui-demo
- rules: anchored-layout-expand, cursor-click-ripple
- voiceover: "בטאב השני — חיפוש דילים חי בכל מועדוני הנאמנות שלכם. מסננים לפי חנות, לפי קטגוריה או בחיפוש חופשי. כל כרטיס נפתח לתנאי ההטבה המלאים: רכישת מינימום, הנחה מרבית, מגבלות שימוש, ואיפה אפשר לממש. קוד הקופון מועתק בלחיצה אחת."
- src: compositions/frames/13-deal-finder.html

## Frame 14 — תובנות · כמה נחסך

- scene: כותרת "הכסף שלכם, מפוענח", בורר התקופה, וה-hero של סכום החיסכון בספירה
- duration: 13s
- transition_in: cut
- status: built
- blueprint: dataviz-countup
- rules: counting-dynamic-scale, control-target-sync
- voiceover: "מסך התובנות מפענח את ההוצאות שלכם לפי תקופה. בראש — כמה כסף Lessley כבר חסכה לכם בפועל, ודרך כמה מועדונים. זה לא אומדן: זה חיסכון שקשור לעסקאות שבאמת קרו."
- src: compositions/frames/14-insights-hero.html

## Frame 15 — תובנות · חמש השקופיות

- scene: הקרוסלה מוחלקת דרך סקירה → קטגוריות → חנויות → עסקאות → חשבונות, כל אחת עם הגרף שלה
- duration: 20s
- transition_in: cut
- status: built
- blueprint: grid-card-assemble
- rules: stat-bars-and-fills, nudge-curve
- voiceover: "מתחת — צלילה לעומק בחמש שקופיות: סקירה כללית משווה את התקופה הזו לקודמת. קטגוריות מראה לאן הכסף באמת הולך. חנויות מובילות — עשר החנויות שאתם קונים בהן הכי הרבה. עסקאות — התנועות האחרונות. וחשבונות — פילוח לפי כל כרטיס מקושר."
- src: compositions/frames/15-insights-slides.html

הסצנה הצפופה ביותר: 5 שקופיות ב-20 שניות = 4 שניות לכל אחת. ההחלקה עצמה היא הקצב,
וכל שקופית נכנסת כשהגרף שלה כבר בתנועה — לא נבנה מאפס.

## Frame 16 — חם

- scene: רשימת הדילים המומלצים נשפכת פנימה; תג "אצור, לא טרנדי" עולה בצד
- duration: 12s
- transition_in: cut
- status: built
- blueprint: grid-card-assemble
- rules: waterfall-entry, spring-pop-entrance
- voiceover: "טאב 'חם' הוא בחירה אצורה של דילים אמיתיים בקטגוריות הגדולות — מכולת, מסעדות, אלקטרוניקה. חשוב להבין: זה לא דירוג פופולריות ולא מה שטרנדי. זו בחירה מקצועית שמתעדכנת באופן שוטף."
- src: compositions/frames/16-hot-deals.html

## Frame 17 — המלצות · התאמות מובילות

- scene: מועדונים מדורגים; טבעת ציון ההתאמה נמשכת ותג "7/10 חנויות תואמות" נוחת
- duration: 15s
- transition_in: cut
- status: built
- blueprint: dataviz-countup
- rules: svg-path-draw, stat-bars-and-fills
- voiceover: "מסך ההמלצות מחושב מתשעים הימים האחרונים שלכם. התאמות מועדונים מובילות — מועדונים שאתם עדיין לא חברים בהם, מדורגים לפי חפיפת חנויות. אם המועדון מכסה שבע מתוך עשר החנויות שאתם קונים בהן — הוא יופיע בראש."
- src: compositions/frames/17-recs-matches.html

## Frame 18 — המלצות · חיסכון שפוספס והחנויות שלך

- scene: שני הטאבים הנותרים; רכישת עבר עם ההנחה שלא נוצלה, ואז תגי הוודאות מדויקת/חזקה/דומה
- duration: 18s
- transition_in: cut
- status: built
- blueprint: comparison-split
- rules: split-tilt-cards, waterfall-entry
- voiceover: "חיסכון שפוספס — רכישות עבר בחנויות שבהן הייתה הנחה זמינה שלא נוצלה. כמה הוצאתם, איפה, ואיזה מועדון היה חוסך לכם שם. והחנויות שלך — מבצעים פעילים דווקא בחנויות שכבר קניתם בהן. כל התאמה מסומנת ברמת ודאות: מדויקת, חזקה, או דומה."
- src: compositions/frames/18-recs-missed.html

`comparison-split` כי אלה שני טאבים שקולים — לא רצף. שלושת תגי הוודאות נוחתים בסוף
כשלישייה, כי זה הפרט שמבדיל את המוצר מניחוש.

## Frame 19 — התראות

- scene: toast צץ בזמן אמת מעל המסך הנוכחי, ואז הפיד נפתח מסודר לפי תגים
- duration: 15s
- transition_in: cut
- status: built
- blueprint: agent-progress-theater
- rules: reactive-displacement, anchored-layout-expand
- voiceover: "כשמנוע הניתוח מסיים לעבוד, ההתראה מגיעה אליכם בזמן אמת — בלי לרענן. הפיד מסודר לפי סוג: ניתוח חיסכון שהושלם, התאמת מועדון חדשה, דיל רלוונטי או עדכון מערכת."
- src: compositions/frames/19-notifications.html

ה-toast חייב להיכנס *מעל* מסך אחר ולא כמסך משלו — זו כל הנקודה של "בזמן אמת".

## Frame 20 — הגדרות

- scene: תפריט ההגדרות; מעבר להעדפות ואז למסך הבנקאות עם הכרטיסים המחוברים
- duration: 15s
- transition_in: cut
- status: built
- blueprint: cursor-ui-demo
- rules: anchored-layout-expand, cursor-click-ripple
- voiceover: "בהגדרות אתם שולטים בהכול: הפרופיל, ההעדפות — עדכון מועדונים, שינוי רמת ההתאמה והשתקת קטגוריות. במסך הבנקאות אפשר לחבר כרטיסים נוספים — כל כרטיס מחובר מדייק עוד יותר את ההתאמות. וכמובן: החלפת שפה והתנתקות בטוחה."
- src: compositions/frames/20-settings.html

## Frame 21 — הסגירה

- scene: הטלפון נסוג למרכז, שלוש הבטחות האבטחה נוחתות, הלוגו נועל את הפריים
- duration: 15s
- transition_in: inverse-zoom
- status: built
- blueprint: logo-assemble-lockup
- rules: waterfall-entry, svg-icon-enrichment
- voiceover: "והכי חשוב — אבטחה ברמה בנקאית. הפרטים מוצפנים בהעברה. אנחנו לעולם לא שומרים סיסמאות בנק. הגישה היא לקריאה בלבד, וניתנת לביטול בכל רגע. המידע שלכם משמש באופן אנונימי בלבד — ולעולם לא נמכר לצד שלישי."
- src: compositions/frames/21-close.html

הסגירה מחזירה את המסגרת של פריים 1 (אותו לוגו, אותו נייבי) — אבל עכשיו הטלפון מלא
בכל מה שראינו. **רייקול, לא חזרה.**
