"""Build detailed 22-chapter TrajectoryLab user manuals (RU and EN)."""
from __future__ import annotations
import os
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "trajectory_lab/ui/resources/manuals"
OUT.mkdir(parents=True, exist_ok=True)
RELEASE = "0.4.2"

windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
font_options = [
    (windir / "Fonts/segoeui.ttf", windir / "Fonts/segoeuib.ttf"),
    (Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")),
]
font_pair = next(((a,b) for a,b in font_options if a.is_file() and b.is_file()), None)
if font_pair is None:
    raise SystemExit("Install Segoe UI or DejaVu Sans to generate the Unicode PDF manuals.")
pdfmetrics.registerFont(TTFont("TL-Regular", str(font_pair[0])))
pdfmetrics.registerFont(TTFont("TL-Bold", str(font_pair[1])))

# Every tuple: title RU/EN, lead RU/EN, body paragraphs RU/EN, table rows RU/EN, note RU/EN.
PAGES = [
("Назначение и область применения", "Purpose and scientific scope",
"TrajectoryLab — локальная научная среда для воспроизводимых экспериментов с поступательным движением жёсткой сферической частицы. Программа объединяет атмосферу, сопротивление среды, гравитацию и численное интегрирование.",
"TrajectoryLab is a local scientific environment for reproducible experiments involving translational motion of a rigid spherical particle. It combines atmosphere, drag, gravity and numerical integration.",
["Базовая модель не описывает ориентацию, вращение, подъёмную силу, деформацию капель, столкновения, стеночные эффекты и сложную геометрию потока. Для таких задач нужна отдельная физическая модель или CFD.", "Используйте программу для учебных, лабораторных и спортивных низкоскоростных экспериментов со сферическими объектами. Всегда учитывайте диапазон применимости корреляции Cd(Re), свойства среды и численную погрешность."],
["The baseline model does not describe orientation, spin, lift, droplet deformation, collisions, wall effects or complex flow geometry. Such tasks require a dedicated model or CFD.", "Use the software for educational, laboratory and sports experiments involving low-speed spherical objects. Always consider the Cd(Re) validity range, medium properties and numerical error."],
[("Подходит", "Сферическая жёсткая частица; поступательное движение."),("Не входит", "Вращение, подъёмная сила, деформация и взаимодействие частиц."),("Проверить", "Геометрию, режим течения и диапазон Re.")],
[("Suitable", "Rigid sphere; translational motion."),("Not included", "Spin, lift, deformation and particle interactions."),("Verify", "Geometry, flow regime and Re range.")],
"Совпадение одной траектории с измерением не доказывает универсальность модели. Проверяйте чувствительность к шагу, атмосфере и Cd.",
"Agreement with one measured path does not prove a model is universal. Test sensitivity to step size, atmosphere and Cd."),
("Установка и первый запуск", "Installation and first launch",
"Распакуйте полный архив в отдельную папку, доступную для записи. Рядом должны находиться build.exe, build.py, pyproject.toml и каталоги проекта. Не запускайте исполняемый файл прямо из окна ZIP.",
"Extract the complete archive into a writable folder. build.exe, build.py, pyproject.toml and project directories must remain together. Do not run the executable from inside the ZIP viewer.",
["Дважды нажмите build.exe. При первом запуске он может скачать официальный установщик Python с python.org, проверить закреплённый SHA-256 и установить частный runtime в профиль текущего пользователя.", "Builder создаёт виртуальное окружение, устанавливает зависимости через pip, проверяет конфликтующие пакеты, запускает pytest и проверку исходников, затем собирает Qt-приложение через PyInstaller.", "После сборки стартовая тема выбирается в Builder. Создаётся ярлык в фактической папке Desktop Windows. Администраторские права и изменение системного PATH не нужны.", "Первоначальная установка требует интернета для python.org и PyPI. Обычные расчёты в готовом приложении локальные и не требуют интернет-соединения."],
["Double-click build.exe. On first launch it may download the official Python installer from python.org, verify the pinned SHA-256 and install a private runtime under the current user's profile.", "Builder creates a virtual environment, installs dependencies with pip, checks package consistency, runs pytest and source checks, then packages the Qt application with PyInstaller.", "After packaging, choose the initial theme in Builder. A shortcut is created in the actual Windows Desktop folder. Administrator privileges and system PATH changes are not required.", "The first setup needs internet access to python.org and PyPI. Ordinary calculations in the packaged application are local and do not require internet."],
[("Платформа", "Windows 10/11 x64."),("Разрешения", "Запись в профиль текущего пользователя."),("Первый запуск", "Интернет нужен только для загрузки runtime и пакетов.")],
[("Platform", "Windows 10/11 x64."),("Permissions", "Write access to the current user's profile."),("First run", "Internet is needed for the runtime and packages.")],
"Если SmartScreen показывает неизвестного издателя, это не равно обнаружению вируса. Не обходите предупреждение о конкретной угрозе.",
"A SmartScreen unknown-publisher warning is not the same as a malware detection. Do not override a specific threat alert."),
("Builder: главное окно", "Builder: main window",
"Builder оформлен как компактная научная утилита: светло-серые панели, тонкие рамки, системный шрифт и моноширинный журнал. Все основные этапы видны в одном рабочем окне.",
"Builder uses a compact scientific-utility layout: light grey panels, thin borders, system UI font and a monospaced journal. Main build stages remain visible in one work window.",
["Флаги RU и EN в верхней части меняют язык подписей, групп, статусов и журнала. Номер версии находится рядом с заголовком и не конкурирует с названием программы.", "Опции сборки включают тесты, очистку предыдущих результатов и режим onedir/onefile. Для обычного релиза используйте onedir и не пропускайте тесты.", "Полоса прогресса показывает текущий этап, а журнал — команды и вывод pip, pytest и PyInstaller. При сбое сохраните весь журнал, включая сообщения выше последней строки.", "После сборки выбор Light/Dark/Soft Pink задаёт стартовую тему приложения. Это сохранённая настройка готовой программы, а не повторная компиляция ядра."],
["The RU and EN flag buttons at the top change labels, groups, statuses and journal language. The version label sits quietly next to the application title.", "Build options include tests, cleanup of previous outputs and onedir/onefile mode. Use onedir for normal distribution and do not skip tests for a release.", "The progress bar shows the current stage; the journal contains commands and output from pip, pytest and PyInstaller. On failure, save the complete journal, not only its last line.", "After packaging, Light/Dark/Soft Pink selects the application's initial theme. This stores a setting; it does not recompile the scientific core."],
[("Язык", "Флаги переключают подписи и сообщения."),("Прогресс", "Этапы: окружение, тесты, PyInstaller, проверка."),("Результат", "Путь к EXE, архиву и ярлыку.")],
[("Language", "Flags switch labels and messages."),("Progress", "Stages: environment, tests, PyInstaller, verification."),("Result", "Paths to executable, archive and shortcut.")],
"Не закрывайте Builder во время установки и упаковки. При сетевой ошибке сначала изучите статус и журнал, а не отключайте защиту Windows.",
"Do not close Builder during installation and packaging. On network errors, inspect status and journal first rather than disabling Windows protection."),
("Первый запуск приложения", "First application start",
"Готовый TrajectoryLab запускается двойным щелчком по EXE или через ярлык. Главное окно восстанавливает сохранённые язык, тему и положение панелей. При первом запуске загружается демонстрационная постановка.",
"Launch the packaged TrajectoryLab by double-clicking its EXE or shortcut. The main window restores saved language, theme and dock layout. A demonstration setup is loaded on first start.",
["Нажмите кнопку расчёта в левой панели или F5. До запуска интерфейс проверит размерности, допустимые диапазоны и конфигурацию модели.", "После расчёта изучите правую панель результатов и центральные вкладки. Если OpenGL недоступен, используйте 2D, временные графики и таблицу — физическое ядро работает отдельно от 3D-визуализации.", "Откройте вакуумный пример и проверьте аналитическое решение. Затем запустите пример с сопротивлением воздуха и проверьте изменение скорости и Reynolds.", "Программа не требует запуска от имени администратора. Если ярлык отсутствует, запустите EXE напрямую из папки dist и проверьте журнал Builder."],
["Click the run button in the left dock or press F5. Before a run, the interface validates dimensions, allowed ranges and model configuration.", "After the run, inspect the results dock and central tabs. If OpenGL is unavailable, use 2D, time-series and table views; the physics core runs independently from 3D visualization.", "Open the vacuum example and verify its analytical solution. Then run the air-resistance example and inspect speed and Reynolds behaviour.", "The application does not need Administrator privileges. If the shortcut is missing, run the EXE directly from dist and inspect the Builder journal."],
[("Пробный запуск", "F5 или кнопка РАСЧЁТ."),("Проверка", "Вакуумный пример перед drag-моделями."),("3D", "Недоступность OpenGL не означает ошибку расчёта.")],
[("Trial run", "F5 or the RUN button."),("Check", "Vacuum example before drag models."),("3D", "Missing OpenGL does not imply a calculation error.")],
"Для первого контроля не меняйте параметры демонстрационного примера: сначала убедитесь, что базовая установка работает.",
"For the first check, do not change the demonstration inputs; first confirm that the baseline installation works."),
("Главное окно: компоновка", "Main window: layout",
"Главное окно построено на QMainWindow: меню и панель инструментов находятся сверху, параметры слева, результаты справа, журнал снизу, а вкладки графиков и таблицы — в центре.",
"The main window is a QMainWindow: menus and toolbar at the top, parameters on the left, results on the right, journal at the bottom, and plot/table tabs in the centre.",
["Меню Файл содержит открытие и сохранение эксперимента, экспорт JSON/CSV/PDF и выход. Меню Эксперимент запускает расчёт и открывает менеджер моделей.", "Меню Вид управляет тремя док-панелями, языком RU/EN и темой Light/Dark/Soft Pink. Скрытая панель возвращается через тот же пункт меню.", "Центральные вкладки: Траектория 2D, Вид 3D, Временные графики и Отсчёты. Выберите вкладку по типу анализа, который нужен в текущий момент.", "Строка состояния показывает готовность, выполнение, успешное завершение или ошибку. Панели можно переставлять и скрывать; их положение сохраняется через настройки Qt."],
["File contains open/save, JSON/CSV/PDF export and exit. Experiment starts a run and opens the model manager.", "View controls three dock panels, RU/EN language and Light/Dark/Soft Pink theme. A hidden panel can be restored through the same menu.", "Central tabs are Trajectory 2D, 3D View, Time Series and Samples. Choose the tab that matches the analysis you need.", "The status bar reports ready, running, completed or failed. Docks can be moved or hidden; their layout is saved through Qt settings."],
[("Слева", "Входные параметры."),("Центр", "Графики и отсчёты."),("Справа", "Сводные результаты."),("Снизу", "Журнал событий.")],
[("Left", "Input parameters."),("Centre", "Plots and samples."),("Right", "Summary results."),("Bottom", "Event journal.")],
"Если исчезла панель, не переустанавливайте программу: сначала откройте меню Вид и верните нужный dock.",
"If a panel disappears, do not reinstall the application; open View first and restore the required dock."),
("Меню Файл и панель инструментов", "File menu and toolbar",
"Меню Файл управляет жизненным циклом эксперимента. Панель инструментов дублирует основные действия и позволяет запускать часто используемые команды без открытия меню.",
"The File menu controls the experiment data lifecycle. The toolbar duplicates core actions so frequent commands can be used without opening a menu.",
["Открыть эксперимент вызывает диалог выбора JSON. После проверки схема загружает параметры и обновляет левую панель.", "Сохранить эксперимент записывает текущую постановку. Это файл входных данных, а не обязательно полный результат численного расчёта.", "Экспорт JSON сохраняет спецификацию, траекторию и provenance. Экспорт CSV создаёт таблицу отсчётов. PDF-экспорт формирует научный отчёт с выбранным языком.", "Ctrl+O открывает файл, Ctrl+S сохраняет, F5 запускает расчёт. Изменение полей сбрасывает старую траекторию, чтобы она не отображалась для новых параметров."],
["Open Experiment opens a JSON picker. After validation, the specification loads and updates the left parameter panel.", "Save Experiment writes the current setup. This is an input file and not necessarily the full numerical output.", "JSON export stores the specification, trajectory and provenance. CSV export creates a sample table. PDF export creates a scientific report in the selected language.", "Ctrl+O opens, Ctrl+S saves and F5 runs. Editing fields clears the old trajectory so it is not shown for new inputs."],
[("Ctrl+O", "Открыть JSON."),("Ctrl+S", "Сохранить постановку."),("F5", "Проверить параметры и запустить расчёт."),("Экспорт", "JSON, CSV или PDF после успешного расчёта.")],
[("Ctrl+O", "Open JSON."),("Ctrl+S", "Save setup."),("F5", "Validate inputs and run."),("Export", "JSON, CSV or PDF after a successful run.")],
"Для воспроизводимости сохраняйте исходный JSON до расчёта и результат JSON после расчёта.",
"For reproducibility, save the input JSON before a run and the result JSON after it."),
("Параметры объекта: масса и диаметр", "Object parameters: mass and diameter",
"Группа Частица находится в верхней части панели параметров. Здесь задаются имя опыта, масса и полный диаметр сферического объекта. Единицы отображаются рядом с числовыми полями.",
"The Particle group sits at the top of the parameter dock. It defines the experiment name, mass and full diameter of the spherical object. Units are displayed beside numeric fields.",
["Масса должна быть конечной и положительной. Поле допускает малые значения для микрочастиц и использует повышенную точность десятичных знаков.", "Диаметр — полный диаметр сферы, не радиус. Он участвует в площади, объёме и числе Reynolds. Если исходно известен радиус, умножьте его на два.", "Плотность частицы не задаётся отдельным полем текущей формы. Плавучая поправка использует массу частицы и вытесненный объём, рассчитанный из диаметра.", "Для несферического тела эквивалентный диаметр не учитывает ориентационную зависимость сопротивления. Такая модель находится вне базового назначения приложения."],
["Mass must be finite and positive. The field supports small micro-particle values with extended decimal precision.", "Diameter is the full sphere diameter, not radius. It is used for area, volume and Reynolds number. If you know radius, multiply it by two.", "Particle density is not a separate field in the current form. Buoyancy correction uses particle mass and displaced volume derived from diameter.", "For a non-spherical object, an equivalent diameter does not account for orientation-dependent drag. Such objects are outside the baseline application scope."],
[("Масса", "kg; строго больше нуля."),("Диаметр", "m; полный диаметр сферы."),("Название", "Подпись для отчёта, не физический параметр.")],
[("Mass", "kg; strictly positive."),("Diameter", "m; full sphere diameter."),("Name", "Report label, not a physical parameter.")],
"Если значение не принимается, проверьте диапазон поля и десятичный разделитель. Размерность проверяется Pint на границе ввода.",
"If a value is rejected, check the field range and decimal separator. Pint validates dimensions at the input boundary."),
("Начальное положение и скорость", "Initial position and velocity",
"Группа Начальное состояние задаёт декартовы координаты и компоненты скорости. Оси x и z горизонтальные, ось y вертикальная и направлена вверх.",
"The Initial State group defines Cartesian coordinates and velocity components. x and z are horizontal; y is vertical and points upward.",
["Начальные x, y, z вводятся в метрах. При включённой остановке на земле начальное y не может быть ниже нуля.", "Компоненты vx, vy, vz вводятся в м/с. Текущая форма использует компоненты скорости; отдельного поля угла возвышения нет. Для наклонного движения разложите скорость на составляющие.", "Положительное vy означает движение вверх, отрицательное — вниз. По умолчанию gravity_y отрицательна, поэтому ускорение направлено по −y.", "Ветер задаётся отдельным вектором. Drag использует относительную скорость v_particle − v_wind, поэтому направление ветра влияет на сопротивление."],
["Initial x, y and z are entered in metres. With ground stopping enabled, initial y cannot be below zero.", "Velocity components vx, vy and vz are entered in m/s. The current form uses components rather than an angle field; resolve an oblique velocity into components.", "Positive vy means upward motion; negative vy means downward motion. Default gravity_y is negative, so acceleration points along −y.", "Wind is a separate vector. Drag uses relative velocity v_particle − v_wind, so wind direction affects resistance."],
[("x/y/z", "Положение в метрах."),("vx/vy/vz", "Скорость в м/с."),("Знак y", "Положительное направление — вверх.")],
[("x/y/z", "Position in metres."),("vx/vy/vz", "Velocity in m/s."),("y sign", "Positive direction is upward.")],
"Проверяйте знаки по простому вакуумному примеру до включения сложной модели сопротивления.",
"Check coordinate signs with a simple vacuum example before enabling a complex drag model."),
("Максимальное время и условия остановки", "Maximum time and stopping conditions",
"Поле времени задаёт верхнюю границу расчёта. Оно не обязывает симуляцию всегда работать ровно столько: при включённом событии поверхности расчёт может закончиться раньше.",
"The time field defines the upper bound of a run. It does not require the simulation to run for that entire duration: with the ground event enabled, the run may end earlier.",
["Фиксированный шаг вывода задаёт интервалы сохранённых отсчётов. Если длительность не кратна шагу, последний интервал сокращается так, чтобы расчёт закончился точно на максимальном времени.", "Флажок остановки при земле активирует первое нисходящее пересечение y=0. RK4 локализует событие внутри шага, DOP853 использует событие solve_ivp.", "Если флажок снят, математическая траектория продолжается до максимального времени даже ниже y=0. Это режим абстрактного расчёта, а не физическая модель прохождения через грунт.", "Для DOP853 шаг вывода не является внутренним адаптивным шагом. Его внутренний размер выбирается решателем по rtol и atol. Для RK4 шаг определяет интегрирование и сетку результатов."],
["The output step defines saved sample spacing. If the duration is not a multiple of the step, the last interval is shortened so the run ends exactly at maximum time.", "The stop-at-ground checkbox enables the first downward crossing of y=0. RK4 localizes the event within its step; DOP853 uses solve_ivp's event mechanism.", "If unchecked, the mathematical path continues to maximum time even below y=0. This is an abstract simulation mode, not a physical model of motion through ground.", "For DOP853 the output step is not the internal adaptive step. The solver chooses internal steps using rtol and atol. For RK4 the step controls integration and saved grid."],
[("Максимальное время", "Верхняя граница времени."),("Шаг вывода", "Интервал между сохранёнными отсчётами."),("Остановка y=0", "Первое пересечение поверхности сверху вниз.")],
[("Maximum time", "Upper time bound."),("Output step", "Spacing between saved samples."),("Stop at y=0", "First downward crossing of the surface.")],
"Если нужно продолжить движение после формального пересечения земли, выключите остановку и явно укажите это допущение в интерпретации.",
"If you need to continue beyond the ground crossing, disable the event and state that assumption explicitly."),
("Среда: гравитация и ветер", "Environment: gravity and wind",
"Группа Среда задаёт вектор гравитации и постоянный вектор ветра. Все компоненты доступны, поскольку физическое ядро интегрирует пространственное состояние.",
"The Environment group defines the gravity vector and a constant wind vector. All components are exposed because the physics core integrates a spatial state.",
["Стандартное значение gravity_y около −9.80665 м/с² означает ускорение вниз. Другие компоненты гравитации обычно равны нулю.", "Ветер вводится в м/с по x, y, z. Положительная компонента указывает направление движения воздуха вдоль положительной оси.", "Текущая форма использует постоянный вектор ветра на всей траектории. Высотно-зависимый или слоистый профиль ветра требует отдельной модели и в текущем интерфейсе не задаётся.", "При выключенном сопротивлении ветровой вектор не меняет траекторию, потому что он входит только в вычисление относительной скорости для drag."],
["The default gravity_y near −9.80665 m/s² represents downward acceleration. Other gravity components are normally zero.", "Wind is entered in m/s along x, y and z. A positive component means air moves along the positive axis direction.", "The current form uses a constant wind vector along the trajectory. Height-dependent or layered wind requires a separate model and is not entered in the current UI.", "With drag disabled, wind does not change the path because it only enters the relative-speed calculation for drag."],
[("gravity_y", "Отрицательное значение — вниз."),("wind_x/y/z", "Скорость воздуха по трём осям."),("Профиль", "В текущей форме ветер постоянный.")],
[("gravity_y", "Negative means downward."),("wind_x/y/z", "Air velocity along three axes."),("Profile", "Wind is constant in the current form.")],
"Не смешивайте ускорение и скорость: у полей разные единицы и разные физические роли.",
"Do not mix acceleration and velocity: these fields have different units and physical roles."),
("Атмосфера и её свойства", "Atmosphere and its properties",
"Атмосферный модуль возвращает плотность ρ, температуру T, динамическую вязкость μ и скорость звука a. Эти величины нужны для вычисления силы сопротивления, Reynolds и Mach.",
"The atmosphere module returns density ρ, temperature T, dynamic viscosity μ and speed of sound a. These properties are needed for drag force, Reynolds and Mach calculations.",
["ISA — стандартный профиль по высоте. Он использует геопотенциальную высоту для слоёв и закон Сазерленда для вязкости. Вводные поля свойств ISA заблокированы, поскольку их задаёт сама модель.", "Постоянная атмосфера фиксирует плотность, температуру и динамическую вязкость. Она полезна для лабораторных условий, когда свойства среды считаются неизменными.", "Экспоненциальная атмосфера задаёт плотность через высоту масштаба и температуру через температурный градиент. Вязкость следует температуре через закон Сазерленда.", "Динамическая вязкость измеряется в Па·с. Не подставляйте вместо неё кинематическую вязкость в м²/с: это другая величина и даст неверный Reynolds."],
["ISA is a standard height profile. It uses geopotential height for layers and Sutherland's law for viscosity. ISA property inputs are disabled because the model defines them.", "Constant atmosphere fixes density, temperature and dynamic viscosity. It is useful for laboratory conditions where the medium is assumed uniform.", "Exponential atmosphere defines density through a scale height and temperature through a lapse rate. Viscosity follows temperature via Sutherland's law.", "Dynamic viscosity is measured in Pa·s. Do not substitute kinematic viscosity in m²/s; it is a different quantity and would produce an incorrect Reynolds number."],
[("ISA", "Стандартная атмосфера."),("Constant", "Постоянные ρ, T, μ."),("Exponential", "Экспоненциальная плотность и профиль температуры.")],
[("ISA", "Standard atmosphere."),("Constant", "Constant ρ, T and μ."),("Exponential", "Exponential density and temperature profile.")],
"Для точного эксперимента используйте измеренные свойства среды, если стандартная атмосфера не соответствует лабораторным условиям.",
"For precision experiments, use measured medium properties when the standard atmosphere does not represent laboratory conditions."),
("Drag-модели и применимость", "Drag models and applicability",
"Встроенный список содержит Stokes, Schiller–Naumann, составную CGW/Clift–Gauvin, постоянный Cd и таблицу Cd(Re). Также доступны пользовательские модели через менеджер.",
"The built-in list includes Stokes, Schiller–Naumann, composite CGW/Clift–Gauvin, constant Cd and tabular Cd(Re). User-defined models are available through the manager.",
["Stokes подходит для очень малых Re и сферического ламинарного обтекания. Cd=24/Re может превышать 100 при малом Re; для встроенной корреляции это допустимо.", "Schiller–Naumann — корреляция сферы с зависимостью Cd от Reynolds в указанном диапазоне. CGW/Clift–Gauvin содержит документированные участки корреляций; учитывайте границы применимости.", "Постоянный Cd — упрощение для ограниченного режима. Он не моделирует переход сопротивления и не является универсальной кривой.", "Таблица Cd(Re) должна содержать возрастающий положительный Re и положительный Cd. Поведение вне диапазона задаётся как error, clamp или extrapolate."],
["Stokes is intended for very low Re and spherical laminar flow. Cd=24/Re can exceed 100 at small Re; this is valid for the built-in correlation.", "Schiller–Naumann is a sphere correlation with Cd depending on Reynolds within its stated range. CGW/Clift–Gauvin combines documented correlation segments; observe applicability limits.", "Constant Cd is a simplification for a limited regime. It does not model drag transitions and is not a universal curve.", "A Cd(Re) table must contain increasing positive Re and positive Cd. Outside-range behaviour is selected as error, clamp or extrapolate."],
[("Stokes / SN", "Корреляции сферического обтекания."),("Constant Cd", "Упрощённая постоянная модель."),("Таблица", "Экспериментальные точки Cd(Re)."),("Validity", "Проверяйте границы и предупреждения.")],
[("Stokes / SN", "Sphere drag correlations."),("Constant Cd", "Simplified constant model."),("Table", "Experimental Cd(Re) points."),("Validity", "Check limits and warnings.")],
"Предупреждение о выходе за validity — это важная научная информация. Не скрывайте его в итоговом отчёте.",
"An applicability warning is important scientific information. Do not omit it from the final report."),
("Численные методы и допуски", "Numerical methods and tolerances",
"RK4 и DOP853 решают одну и ту же систему уравнений, но по-разному управляют шагом и оценкой ошибки. Сравнивать их следует по физическим величинам и допускам.",
"RK4 and DOP853 solve the same equations but handle step size and error control differently. Compare them using physical quantities and tolerances.",
["RK4 выполняет четыре вычисления правой части на шаге. На каждой стадии обновляются высота, атмосфера, относительная скорость, Reynolds и Cd.", "DOP853 использует адаптивное интегрирование SciPy. rtol задаёт относительный допуск, atol — абсолютный; допускается векторный atol для компонентов состояния.", "Для регрессионного контроля фиксируйте RK4 и шаг. Для независимой проверки сравните с DOP853, сохранив оба допуска и версию SciPy.", "Визуально гладкая линия не является доказательством сходимости. Проверяйте апогей, время события, смещение, конечную скорость и изменение результата при уменьшении шага."],
["RK4 evaluates the right-hand side four times per step. Height, atmosphere, relative speed, Reynolds and Cd are refreshed at each stage.", "DOP853 uses adaptive SciPy integration. rtol is the relative tolerance, atol is absolute; a vector atol may be used for state components.", "For regression control, fix RK4 and the step. For an independent check, compare with DOP853 and record both tolerances and the SciPy version.", "A visually smooth line does not prove convergence. Check apogee, event time, displacement, final speed and changes under smaller steps."],
[("RK4", "Фиксированный шаг."),("DOP853", "Адаптивный шаг."),("rtol/atol", "Контроль локальной численной ошибки.")],
[("RK4", "Fixed step."),("DOP853", "Adaptive steps."),("rtol/atol", "Control local numerical error.")],
"Шаг вывода DOP853 не управляет его внутренним адаптивным шагом. Для точности изменяйте rtol/atol.",
"The DOP853 output step does not control its internal adaptive step. Change rtol/atol to control accuracy."),
("Запуск расчёта и проверка параметров", "Running and validating a calculation",
"Кнопка РАСЧЁТ собирает значения формы, проверяет их схемой Pydantic и размерности Pint, конвертирует физические величины к SI и запускает расчёт в отдельном потоке.",
"The RUN button collects form values, validates them through Pydantic and Pint, converts quantities to SI and starts the calculation in a separate worker thread.",
["Если значение не является конечным положительным числом там, где это требуется, или имеет несовместимую размерность, расчёт не стартует. Сообщение валидации указывает поле или условие, требующее исправления.", "Отдельный QThread не позволяет численному расчёту блокировать перерисовку основного окна. Повторный запуск недоступен, пока выполняется текущая задача.", "Предупреждения о применимости drag-модели записываются в журнал. Предупреждение может сопровождать успешный расчёт, но его нужно учитывать при интерпретации.", "После изменения любого входного поля старый результат очищается. Это предотвращает ошибочное отображение траектории, вычисленной с предыдущими параметрами."],
["If a required value is non-finite/non-positive or dimensionally inconsistent, the run does not start. The validation message identifies the field or condition to fix.", "A separate QThread prevents numerical work from blocking the main window. A second run is disabled while the current task is active.", "Drag applicability warnings are written to the journal. A warning may accompany a successful run, but it must be considered when interpreting the result.", "Editing any input clears the old result. This prevents a trajectory from previous parameters being mistaken for the current setup."],
[("Проверка", "Pydantic + Pint."),("Выполнение", "Отдельный поток расчёта."),("После изменения", "Старая траектория сбрасывается.")],
[("Validation", "Pydantic + Pint."),("Execution", "Separate calculation thread."),("After edits", "Previous trajectory is cleared.")],
"Перед длительной серией расчётов сохраните постановку JSON.",
"Save the experiment JSON before a long series of runs."),
("Траектория 2D", "Trajectory 2D",
"Вкладка 2D отображает проекцию x-y: x по горизонтали, y по вертикали. Это основной вид для анализа высоты и горизонтального смещения.",
"The 2D tab displays the x-y projection: x horizontally and y vertically. It is the primary view for height and horizontal displacement analysis.",
["Вертикальная линия при постоянном x и меняющемся y ожидаема для чистого вертикального падения. Она не означает неисправность графика.", "Автомасштаб подстраивает оси по данным. Если боковое смещение очень мало, кривая будет визуально почти вертикальной.", "При включённой остановке на земле последняя точка соответствует y=0. При отключённой остановке расчёт может продолжаться ниже нуля до максимального времени.", "Для проверки наклонного движения задайте ненулевые vx и vy. Без сопротивления при постоянной гравитации траектория имеет параболическую форму."],
["A vertical line with constant x and changing y is expected for pure vertical falling. It does not indicate a plotting defect.", "Auto scaling fits the axes to the data. If lateral displacement is very small, the path will look almost vertical.", "With ground stopping enabled, the last point is y=0. With stopping disabled, the calculation may continue below zero until maximum time.", "For an oblique path, set nonzero vx and vy. Without drag and with constant gravity, the path is parabolic."],
[("x", "Горизонтальная координата."),("y", "Высота, ось вверх."),("Вертикальная линия", "Ожидаема при отсутствии бокового движения.")],
[("x", "Horizontal coordinate."),("y", "Height, upward axis."),("Vertical line", "Expected without lateral motion.")],
"Для точных координат используйте вкладку Отсчёты, а не оценивайте положение по пикселям.",
"Use the Samples tab for exact coordinates rather than estimating from screen pixels."),
("Вид 3D", "3D View",
"3D-вкладка показывает пространственную траекторию по x, y и z. Она полезна для анализа бокового смещения, но зависит от OpenGL и драйвера видеокарты.",
"The 3D tab displays the spatial path in x, y and z. It is useful for lateral displacement analysis but depends on OpenGL and the graphics driver.",
["Вращайте сцену мышью, чтобы рассмотреть траекторию с разных направлений. Колёсико обычно изменяет масштаб; конкретное поведение зависит от реализации OpenGL-виджета.", "Сравнивайте 3D-сцену с численными x/y/z в таблице. Если z постоянно, траектория должна оставаться в плоскости x-y.", "Если OpenGL недоступен, проверьте 2D и таблицу. Ошибка визуализатора не означает, что физическое ядро не выполнило расчёт.", "Для диагностики укажите модель GPU, версию драйвера и сообщение журнала. Попробуйте локальный сеанс Windows, если приложение запущено через удалённый рабочий стол."],
["Rotate the scene with the mouse to inspect the path from different directions. The wheel usually changes scale; exact behaviour depends on the OpenGL widget.", "Compare the scene with numeric x/y/z in the table. If z is constant, the path should remain in the x-y plane.", "If OpenGL is unavailable, check 2D and the sample table. A visualization error does not mean the physics core failed.", "For diagnosis, provide the GPU model, driver version and journal message. Try a local Windows session if the application is running through Remote Desktop."],
[("x-y", "Вертикальная плоскость."),("z", "Боковое смещение."),("OpenGL", "Зависит от драйвера GPU.")],
[("x-y", "Vertical plane."),("z", "Lateral displacement."),("OpenGL", "Depends on GPU driver.")],
"3D-сцена — представление уже рассчитанной траектории, а не отдельный решатель.",
"The 3D scene visualizes an already calculated path; it is not a separate solver."),
("Временные графики", "Time-series plots",
"Вкладка временных графиков отображает скорость, число Mach и кинетическую энергию. Все величины относятся к одному результату и имеют общий временной аргумент.",
"The Time Series tab displays speed, Mach number and kinetic energy. All quantities belong to the same result and share the same time axis.",
["Скорость — модуль скорости частицы. Она отличается от скорости относительно воздуха, используемой в сопротивлении при наличии ветра.", "Mach рассчитывается как относительная скорость потока, делённая на локальную скорость звука. Атмосферная температура и высота могут менять скорость звука.", "Кинетическая энергия равна 1/2 m v² и использует скорость частицы. Для постоянной массы форма энергии связана с квадратом скорости.", "При падении из покоя скорость обычно растёт. При сопротивлении рост может замедляться по мере приближения к терминальной скорости, если этот режим достигается в интервале."],
["Speed is particle speed magnitude. It differs from air-relative speed used in drag when wind is present.", "Mach is flow-relative speed divided by local speed of sound. Atmospheric temperature and height may change sound speed.", "Kinetic energy is 1/2 m v² and uses particle speed. For constant mass, energy follows the square of speed.", "For a drop from rest, speed normally increases. With drag, the increase may slow as terminal speed is approached if that regime is reached within the run."],
[("Speed", "Модуль скорости частицы, м/с."),("Mach", "Относительная скорость / скорость звука."),("Energy", "Кинетическая энергия, Дж.")],
[("Speed", "Particle speed magnitude, m/s."),("Mach", "Relative speed / speed of sound."),("Energy", "Kinetic energy, J.")],
"При ветре не путайте скорость частицы и относительную скорость воздуха: они используются в разных величинах.",
"With wind, do not confuse particle speed and air-relative speed; they are used in different quantities."),
("Таблица отсчётов", "Samples table",
"Таблица показывает сохранённые временные точки траектории: координаты, компоненты скорости, модуль скорости, Mach, энергию, Reynolds и Cd.",
"The table displays saved trajectory time samples: coordinates, velocity components, speed magnitude, Mach, energy, Reynolds and Cd.",
["RK4 обычно выдаёт точки с фиксированным шагом, а последний шаг может быть укорочен. DOP853 выдаёт запрошенную сетку и добавляет локализованную точку события, если срабатывает остановка.", "Моноширинный шрифт и выравнивание помогают сравнивать значения. Заголовки содержат единицы. Сортировка отключена, чтобы сохранялся временной порядок.", "При нулевой относительной скорости начальные Reynolds и Cd могут быть нулевыми диагностическими значениями, поскольку сила сопротивления не рассчитывается при нулевом потоке.", "Для передачи данных в Excel, Python или R используйте экспорт CSV — он сохраняет порядок и численную точность лучше ручного копирования."],
["RK4 generally outputs fixed-step points; the last step may be shortened. DOP853 returns the requested grid and appends a localized event point when stopping is triggered.", "Monospaced text and alignment help compare values. Headers include units. Sorting is disabled to preserve time order.", "At zero relative speed, initial Reynolds and Cd may be zero diagnostic values because drag is not evaluated at zero flow.", "Use CSV export for Excel, Python or R; it preserves order and numeric precision better than manual copying."],
[("t", "Время в секундах."),("x/y/z", "Положение в метрах."),("v", "Скорости в м/с."),("Re/Cd", "Безразмерные показатели.")],
[("t", "Time in seconds."),("x/y/z", "Position in metres."),("v", "Velocity in m/s."),("Re/Cd", "Dimensionless indicators.")],
"Не сортируйте таблицу по произвольному столбцу, если анализируете последовательность движения.",
"Do not sort by an arbitrary column when analysing the chronological path."),
("Правая панель результатов", "Results dock",
"Правая панель отображает краткую сводку: смещение, время расчёта, событие земли, максимальную высоту, время апогея, скорость, Mach, Reynolds, энергию и checksum.",
"The right dock displays a summary: displacement, elapsed time, ground event, maximum height, apogee time, speed, Mach, Reynolds, energy and checksum.",
["Фактическое время расчёта может быть меньше максимального времени, если сработало событие земли. Если событие не наступило, UI показывает, что оно не достигнуто.", "Максимальная высота интерполируется между соседними отсчётами с использованием положения и вертикальной скорости. Поэтому апогей может находиться между строками таблицы.", "Максимальная скорость, Mach и Reynolds вычисляются по сохранённым точкам. Конечная энергия относится к последнему состоянию траектории.", "Checksum строится по квантованным столбцам для контроля регрессий. Это не обещание полного побитового совпадения между любыми процессорами."],
["Actual elapsed time may be shorter than maximum time when the ground event fires. If no event occurs, the UI reports that it was not reached.", "Maximum height is interpolated between neighbouring samples using position and vertical velocity. The apogee may therefore lie between table rows.", "Maximum speed, Mach and Reynolds are evaluated over saved points. Final energy belongs to the last trajectory state.", "The checksum is based on quantized columns for regression detection. It does not promise bitwise identity across all CPUs."],
[("Apogee", "Интерполированный максимум y."),("Impact", "Время первого события y=0."),("Checksum", "Квантованный контрольный хэш.")],
[("Apogee", "Interpolated maximum y."),("Impact", "First y=0 event time."),("Checksum", "Quantized regression hash.")],
"Если число выглядит неожиданным, проверьте входные параметры, единицы и соответствующие отсчёты.",
"If a value looks unexpected, inspect the inputs, units and corresponding samples."),
("Сохранение и открытие эксперимента", "Saving and opening experiments",
"JSON-эксперимент — переносимое описание постановки задачи. Он содержит физические величины с единицами, атмосферу, модель сопротивления, метод и настройки интегратора.",
"An experiment JSON is a portable description of the problem setup. It contains dimensional inputs with units, atmosphere, drag model, method and integrator settings.",
["Сохраните эксперимент через File → Save. Используйте описательное имя, не включающее личные сведения, если файл планируется передавать коллегам.", "Откройте файл через File → Open. Pydantic проверяет схему, Pint проверяет единицы и переводит значения к SI. Неизвестные поля и неверные размерности должны приводить к отказу загрузки.", "Встроенная табличная модель может храниться в самом JSON. Для plugin:<id> на принимающем компьютере потребуется соответствующая пользовательская модель; проверяйте Python-код отдельно.", "После открытия сверьте массу, диаметр, начальное состояние, атмосферу, drag, метод и длительность до запуска расчёта."],
["Save the experiment through File → Save. Use a descriptive name that does not contain personal information if the file will be shared.", "Open it through File → Open. Pydantic validates the schema and Pint checks units and converts them to SI. Unknown fields and invalid dimensions should fail validation.", "A tabular model can be embedded in JSON. A plugin:<id> requires the corresponding user model on the receiving computer; review Python source separately.", "After loading, review mass, diameter, initial state, atmosphere, drag, method and duration before running."],
[("Сохранение", "Входная постановка."),("Проверка", "Схема и физические размерности."),("Перед запуском", "Визуальная сверка параметров.")],
[("Save", "Input setup."),("Validation", "Schema and physical dimensions."),("Before run", "Review parameters visually.")],
"Успешный импорт означает, что формат прошёл проверку, но не гарантирует научную применимость параметров.",
"Successful import means the format passed validation; it does not guarantee scientific applicability."),
("Экспорт JSON и CSV", "JSON and CSV export",
"Экспорт результата JSON сохраняет постановку, траекторию и метаданные воспроизводимости. CSV удобен для внешней обработки численных отсчётов.",
"Result JSON stores the setup, trajectory and reproducibility metadata. CSV is convenient for external processing of numeric samples.",
["В JSON включаются версии приложения, Python, NumPy, SciPy и Pint, платформа, интегратор, шаг или допуски, seed, описание модели, SHA-256 модели и траектории.", "CSV содержит временные ряды и производные величины. При открытии в Excel проверьте разделитель и десятичный символ: локальные настройки могут менять способ импорта.", "Checksum помогает заметить регрессию, но не указывает, какая величина изменилась. Для сравнения используйте отдельные физические допуски.", "Перед публичной отправкой проверьте имя эксперимента, метаданные, комментарии и имя файла: пользователь может случайно включить туда личные сведения."],
["JSON includes application, Python, NumPy, SciPy and Pint versions, platform, integrator, step or tolerances, seed, model description, model SHA-256 and trajectory SHA-256.", "CSV contains time series and derived quantities. When opening it in Excel, check delimiter and decimal separator because locale settings may change import behaviour.", "A checksum can reveal a regression but does not identify which quantity changed. Use separate physical tolerances for comparison.", "Before public sharing, inspect experiment name, metadata, comments and filename for accidental personal information."],
[("JSON", "Постановка + результат + provenance."),("CSV", "Табличные отсчёты."),("Обмен", "Проверить метаданные и имена файлов.")],
[("JSON", "Setup + result + provenance."),("CSV", "Tabular samples."),("Sharing", "Check metadata and filenames.")],
"Не редактируйте checksum вручную; после изменения данных создайте новый результат.",
"Do not edit a checksum manually; create a new result after changing data."),
("PDF-отчёт и выбор языка", "PDF report and language selection",
"PDF-отчёт собирает параметры эксперимента, модель, применимость, результаты, численный метод, provenance, предупреждения и графики.",
"The PDF report combines experiment parameters, model, applicability, results, numerical method, provenance, warnings and plots.",
["Выберите File → Export Scientific PDF Report, имя файла и язык: русский, English или двуязычный режим. Для кириллицы требуется Unicode-шрифт.", "Проверьте заголовок, таблицу параметров, метаданные drag-модели, шаг и допуски, seed, версии библиотек и два контрольных хэша.", "Двуязычный отчёт длиннее и подходит для передачи между лабораториями. Русский и английский режимы сохраняют один набор научных данных, переводятся только заголовки и описания.", "Сохраняйте PDF вместе с исходным JSON и результатом JSON, если требуется воспроизводимый пакет."],
["Choose File → Export Scientific PDF Report, filename and language: Russian, English or bilingual. A Unicode font is required for Cyrillic.", "Check title, parameter table, drag-model metadata, step and tolerances, seed, library versions and both control hashes.", "The bilingual report is longer and suitable for inter-laboratory exchange. Language modes share the same scientific data; only headings and descriptions are translated.", "Keep the PDF together with input JSON and result JSON when a reproducible package is required."],
[("Русский", "Отчёт с русскими заголовками."),("English", "Report with English headings."),("RU + EN", "Двуязычный документ.")],
[("Russian", "Report with Russian headings."),("English", "Report with English headings."),("RU + EN", "Bilingual document.")],
"PDF документирует вычисление, но не удостоверяет корректность выбранной физической корреляции.",
"A PDF documents the calculation; it does not certify the selected physical correlation."),
("Менеджер моделей", "Drag Model Manager",
"Менеджер доступен из Experiment → Drag Model Manager. Он показывает встроенные и пользовательские модели, импортирует таблицы и Python-файлы и обновляет каталог.",
"The manager is available from Experiment → Drag Model Manager. It lists built-in and user models, imports tables and Python files and refreshes the registry.",
["Пользовательские модели хранятся в каталоге .trajectory_lab/models профиля пользователя. Встроенные модели входят в приложение и не должны удаляться как пользовательские.", "Перед выбором проверьте имя, версию, автора, источник, геометрию и диапазон Reynolds. Источник должен быть прослеживаемым.", "JSON/CSV таблицы читаются как данные и не запускают Python. Они предпочтительнее для передачи простых зависимостей Cd(Re).", "Изменение модели сбрасывает предыдущий расчёт. Выполните новый запуск и сохраните обновлённую provenance-запись."],
["User models are stored in the user's .trajectory_lab/models directory. Built-in models ship with the application and should not be removed as user models.", "Before selection, check name, version, author, source, geometry and Reynolds range. The source should be traceable.", "JSON/CSV tables are parsed as data and do not execute Python. Prefer them for simple Cd(Re) relationships.", "Changing the model invalidates the previous run. Recalculate and save updated provenance."],
[("Refresh", "Перечитать каталог."),("Import table", "Добавить JSON/CSV."),("Import Python", "Копировать код; запуск — отдельное подтверждение.")],
[("Refresh", "Read the model directory."),("Import table", "Add JSON/CSV."),("Import Python", "Copy source; execution requires confirmation.")],
"Наличие записи в менеджере не означает, что модель подходит к диапазону конкретного эксперимента.",
"A model appearing in the manager does not mean it is valid for a particular experiment range."),
("Табличные модели Cd(Re)", "Tabular Cd(Re) models",
"Табличная модель задаёт пары Reynolds и Cd. Reynolds должен быть положительным и строго возрастать; Cd должен быть конечным и положительным.",
"A tabular model stores Reynolds/Cd pairs. Reynolds must be positive and strictly increasing; Cd must be finite and positive.",
["Импортируйте CSV с колонками Reynolds и Cd или заполните редактор вручную. Проверьте заголовки, разделитель, десятичную точку и крайние точки таблицы.", "Linear соединяет точки в обычных координатах. Log-log интерполирует в логарифмах Re и Cd и подходит для степенных участков. Кубическая log-log может сглаживать кривую, но на редких данных создавать осцилляции.", "Политика error прерывает расчёт вне таблицы. Clamp удерживает крайнее значение. Extrapolate продолжает зависимость за измеренный диапазон и требует обоснования.", "Указывайте геометрию, источник, автора и версию. Не представляйте демонстрационную таблицу как экспериментальные данные."],
["Import a CSV with Reynolds and Cd columns or fill the editor manually. Check headers, delimiter, decimal separator and the edge points.", "Linear interpolation connects points in ordinary coordinates. Log-log interpolates in logarithmic Re and Cd and suits power-law sections. Cubic log-log may smooth a curve but oscillate on sparse data.", "Error stops the run outside the table. Clamp holds the nearest endpoint. Extrapolate extends the curve beyond measured data and requires justification.", "Record geometry, source, author and version. Do not present a demonstration table as experimental data."],
[("Linear", "Обычная линейная интерполяция."),("Log-log", "Интерполяция в логарифмических координатах."),("Outside", "Error / clamp / extrapolate.")],
[("Linear", "Ordinary linear interpolation."),("Log-log", "Interpolation in logarithmic coordinates."),("Outside", "Error / clamp / extrapolate.")],
"Не экстраполируйте далеко за измеренный диапазон без независимой проверки.",
"Do not extrapolate far beyond the measured range without independent validation."),
("Python-плагины и безопасность", "Python plugins and security",
"Python-плагин — исполняемый код. Интерфейс BaseDragModel гарантирует только ожидаемые методы, но не безопасность. Код выполняется с правами текущего пользователя Windows.",
"A Python plugin is executable code. BaseDragModel defines the expected methods, but it does not provide security isolation. Code runs with the current Windows user's permissions.",
["Откройте исходник в редакторе и разберите его импорты и побочные действия. Внимательно проверяйте subprocess, os, socket, urllib, requests, ctypes, winreg и динамическое исполнение.", "Не скачивайте неизвестные плагины с форумов. Не запускайте программу администратором для работы с плагином. Python-код может читать и изменять файлы, запускать процессы и обращаться к сети.", "CLI не загружает Python-плагины по умолчанию; для этого нужен явный --allow-python-plugins. GUI требует подтверждение перед запуском.", "Если модель можно описать точками, используйте JSON/CSV: декларативная таблица не выполняет произвольный Python."],
["Open source in an editor and inspect imports and side effects. Pay attention to subprocess, os, socket, urllib, requests, ctypes, winreg and dynamic execution.", "Do not download unknown plugins from forums. Do not run the application as Administrator for plugin use. Python code may read and modify files, start processes and access the network.", "The CLI does not load Python plugins by default; the explicit --allow-python-plugins flag is required. The GUI asks for confirmation before execution.", "If a model can be represented by points, use JSON/CSV: a declarative table does not execute arbitrary Python."],
[("JSON/CSV", "Предпочтительный формат данных."),("Python", "Требуется аудит исходника."),("Sandbox", "Полной изоляции нет.")],
[("JSON/CSV", "Preferred data format."),("Python", "Source review required."),("Sandbox", "No full isolation is provided.")],
"Предупреждение интерфейса не делает недоверенный Python-код безопасным.",
"A UI warning does not make untrusted Python code safe."),
("Язык, тема и панели", "Language, themes and docks",
"Меню Вид управляет языком, темой и видимостью док-панелей. RU/EN переключается без перезапуска через каталоги переводов; темы применяются через QSS.",
"The View menu controls language, theme and dock visibility. RU/EN switches without restart through translation catalogs; themes are applied through QSS.",
["View → Language переключает русский и английский язык. Каталог перевода должен обновлять заголовки меню, панели, вкладки, таблицу и сообщения.", "View → Theme предлагает Light, Dark и Soft Pink. Розовая тема использует пастельный акцент, сохраняя нейтральные панели и технический стиль.", "Панели Parameters, Results и Journal можно скрыть или вернуть через View. Размеры и состояние окна сохраняются в QSettings.", "При обновлении программы не удаляйте пользовательские настройки, если хотите сохранить язык, тему и компоновку."],
["View → Language switches Russian and English. The catalog should update menu headings, docks, tabs, table and messages.", "View → Theme offers Light, Dark and Soft Pink. Pink uses a pastel accent while retaining neutral panels and a technical style.", "Parameters, Results and Journal docks can be hidden or restored through View. Window size and state are saved in QSettings.", "Do not delete user settings during an update if you want to retain language, theme and layout."],
[("Language", "RU/EN без перезапуска."),("Theme", "Light/Dark/Soft Pink."),("Docks", "Показать или скрыть панели.")],
[("Language", "RU/EN without restart."),("Theme", "Light/Dark/Soft Pink."),("Docks", "Show or hide panels.")],
"Переключение темы не изменяет параметры эксперимента и результаты.",
"Changing the theme does not modify experiment inputs or results."),
("Локальные данные и приватность", "Local data and privacy",
"Основное приложение работает локально. Настройки, пользовательские модели и журналы сохраняются в профиле текущего пользователя; проект не содержит встроенной отправки телеметрии или экспериментальных файлов.",
"The main application operates locally. Settings, user models and logs are stored in the current user's profile; the project has no built-in telemetry or experiment-file upload.",
["Обычно пользовательские данные находятся в %USERPROFILE%\\.trajectory_lab. Там могут быть папки models и logs, а также настройки. Не публикуйте этот каталог целиком.", "Локальный фильтр журналов заменяет известные корни пользовательских путей, но не является универсальным средством удаления персональных данных. Перед отправкой проверьте журнал вручную.", "Builder обращается к python.org и PyPI при установке runtime и библиотек. Это сетевое поведение относится к первичной сборке, а не к расчётам в основном приложении.", "Python-плагины могут самостоятельно выходить в сеть и передавать данные. Поэтому загружайте только проверенный код. SHA-256 удостоверяет идентичность файла, но не его доброкачественность."],
["User data are normally stored in %USERPROFILE%\\.trajectory_lab. It may contain models, logs and settings. Do not publish the whole directory.", "The local log filter replaces known user path roots but is not a universal personal-data scrubber. Review logs manually before sharing.", "Builder contacts python.org and PyPI when installing the runtime and libraries. This network activity belongs to initial setup, not to calculations in the desktop application.", "Python plugins can access the network and transmit data independently. Load only reviewed code. SHA-256 proves file identity, not benign behaviour."],
[("Локально", "Настройки, модели, логи и сохранённые эксперименты."),("Builder", "python.org и PyPI при первой сборке."),("Плагины", "Могут выполнять произвольные сетевые действия.")],
[("Local", "Settings, models, logs and saved experiments."),("Builder", "python.org and PyPI during first build."),("Plugins", "May perform arbitrary network actions.")],
"Перед публикацией JSON, CSV, PDF и журналов удалите названия, пути и значения, которые не должны быть публичными.",
"Before publishing JSON, CSV, PDF or logs, remove names, paths and values that should remain private."),
("Воспроизводимость и контрольные хэши", "Reproducibility and checksums",
"Provenance результата фиксирует версию программы, Python, NumPy, SciPy и Pint, ОС, интегратор, шаг, допуски, seed, модель и её SHA-256.",
"Result provenance records the application, Python, NumPy, SciPy and Pint versions, OS, integrator, step, tolerances, seed, model and its SHA-256.",
["Для RK4 фиксируйте шаг и версии зависимостей. Для DOP853 сохраняйте rtol и atol. Сравнивайте отдельные физические величины по заданным допускам.", "Траекторный checksum использует нормализацию и квантование по столбцам. Он полезен для обнаружения регрессий, но не обещает побитового совпадения на разных процессорах.", "Seed сохраняется для аудита и будущих стохастических расширений. В детерминированных примерах seed может не влиять на результат.", "Для научного обмена храните входной JSON, результат JSON, CSV и PDF вместе с описанием версии среды."],
["For RK4, fix the step and dependency versions. For DOP853, store rtol and atol. Compare individual physical quantities against defined tolerances.", "The trajectory checksum uses per-column normalization and quantization. It helps detect regressions but does not promise bitwise identity across CPUs.", "Seed is stored for audit and future stochastic extensions. It may not affect deterministic examples.", "For scientific exchange, keep input JSON, result JSON, CSV and PDF with the environment version description."],
[("Вход", "JSON и параметры модели."),("Численный контроль", "Шаг или rtol/atol."),("Проверка", "Допуски по величинам + checksum.")],
[("Input", "JSON and model parameters."),("Numerical control", "Step or rtol/atol."),("Check", "Per-quantity tolerances + checksum.")],
"Один несовпадающий checksum не объясняет причину изменения: сравните значения и версии программного окружения.",
"A checksum mismatch alone does not explain the cause; compare values and software environment versions."),
("Вакуумный эталон", "Vacuum reference case",
"Пример vacuum_reference.json отключает сопротивление и использует постоянную гравитацию. Это контрольный случай с аналитическим решением.",
"The vacuum_reference.json example disables drag and uses constant gravity. It is a reference case with an analytical solution.",
["Откройте пример и проверьте положение, скорость, g, максимальное время, шаг и метод до запуска.", "Для вертикальной координаты используйте y(t)=y0+vy0·t+0.5·g_y·t². Для горизонтальной координаты без горизонтальных сил x(t)=x0+vx0·t.", "Если vx=0, график x-y будет вертикальным. Если vy положительна, объект сначала поднимается; после апогея вертикальная скорость меняет знак.", "Сравните время апогея, максимальную высоту, конечную скорость и время события с аналитическими значениями в пределах численного допуска."],
["Open the example and check position, velocity, g, maximum time, step and method before running.", "For vertical position use y(t)=y0+vy0·t+0.5·g_y·t². With no horizontal forces, x(t)=x0+vx0·t.", "If vx=0, the x-y graph is vertical. If vy is positive, the object first rises; after apogee, vertical velocity changes sign.", "Compare apogee time, maximum height, final speed and event time with analytical values within numerical tolerance."],
[("Цель", "Проверить координаты и интегратор."),("Сопротивление", "Выключено."),("График", "Вертикальная линия возможна при vx=0.")],
[("Purpose", "Check coordinates and integrator."),("Drag", "Disabled."),("Plot", "A vertical line is possible when vx=0.")],
"Не переходите к интерпретации drag, пока вакуумный эталон не совпадает с аналитикой.",
"Do not interpret drag results until the vacuum reference agrees with the analytical solution."),
("Пример с сопротивлением", "Air-resistance example",
"Пример air_resistance_drop.json использует ISA и Schiller–Naumann для падения сферической частицы. Он проверяет связку атмосфера → вязкость → Reynolds → Cd → ускорение.",
"The air_resistance_drop.json example uses ISA and Schiller–Naumann for a falling sphere. It checks the atmosphere → viscosity → Reynolds → Cd → acceleration chain.",
["Убедитесь, что выбраны ISA и Schiller–Naumann, и проверьте массу, диаметр, начальную высоту и шаг вывода.", "Скорость из покоя должна возрастать. При сопротивлении рост может постепенно замедляться по мере приближения к терминальной скорости; конечный интервал может быть слишком коротким для достижения предела.", "Re=ρ·v_rel·d/μ использует диаметр. Mach определяется относительно локальной скорости звука. Сверьте таблицу и временные графики.", "Если журнал содержит предупреждение о диапазоне применимости, включите его в интерпретацию и не сравнивайте модель за пределами заявленных условий."],
["Confirm ISA and Schiller–Naumann; review mass, diameter, initial height and output step.", "Speed should rise from rest. With drag, its growth may slow as terminal speed is approached; a finite interval may be too short to reach it.", "Re=ρ·v_rel·d/μ uses diameter. Mach is based on local speed of sound. Check the table and time-series plots.", "If the journal reports an applicability warning, include it in the interpretation and do not compare the model beyond its stated conditions."],
[("Speed", "Изменяется во времени."),("Re", "Зависит от ρ, v, d и μ."),("Cd", "Зависит от выбранной корреляции.")],
[("Speed", "Changes over time."),("Re", "Depends on ρ, v, d and μ."),("Cd", "Depends on the selected correlation.")],
"Параметры демонстрационного примера не заменяют протокол калибровки собственной лаборатории.",
"Demonstration inputs do not replace calibration of your own laboratory setup."),
("Журнал и устранение неполадок", "Journal and troubleshooting",
"Журнал фиксирует сообщения приложения и расчёта. Для поиска причины сохраняйте сообщения до ошибки, а не только последнюю строку.",
"The journal records application and calculation messages. To diagnose a problem, keep the messages leading up to the failure, not only the final line.",
["При ошибке расчёта сохраните JSON, метод, атмосферу, drag-модель и журнал. Укажите версию приложения и минимальные шаги воспроизведения.", "При проблеме 3D укажите GPU и драйвер. Если таблица и 2D содержат данные, проблема может быть только в OpenGL-представлении.", "При ошибке Builder сохраните полный лог этапа, версию Windows, статус сети и точное сообщение pip или PyInstaller.", "Перед отправкой лога вручную удалите персональные пути, имена файлов и научные данные, которые вы не хотите раскрывать."],
["For a calculation failure, save JSON, method, atmosphere, drag model and journal. Include application version and minimal reproduction steps.", "For a 3D issue, provide GPU and driver. If the table and 2D view contain data, the issue may be limited to OpenGL rendering.", "For a Builder failure, save the complete stage log, Windows version, network status and exact pip/PyInstaller message.", "Before sharing logs, manually remove personal paths, filenames and research data you do not want to disclose."],
[("Расчёт", "JSON + журнал + параметры."),("3D", "GPU и драйвер."),("Builder", "Полный лог сборки.")],
[("Calculation", "JSON + journal + inputs."),("3D", "GPU and driver."),("Builder", "Full build log.")],
"Не отправляйте всю папку .trajectory_lab: она может содержать модели и пользовательские эксперименты.",
"Do not send the entire .trajectory_lab folder; it may contain user models and experiments."),
("Обновление и резервная копия", "Updates and backups",
"Папка приложения и пользовательские данные разделены. При обновлении можно заменить каталог программы, оставив .trajectory_lab в профиле пользователя.",
"The application folder and user data are separate. During an update, replace the application directory while retaining .trajectory_lab in the user profile.",
["Закройте программу и сделайте резервную копию пользовательского каталога. В Windows его типичное расположение — %USERPROFILE%\\.trajectory_lab.", "Распакуйте новую версию отдельно и проверьте запуск до удаления предыдущей. Не распаковывайте обновление поверх работающего приложения.", "Переносите только необходимые пользовательские модели. Перед копированием .py файлов проверьте их исходник; JSON/CSV таблицы проще и безопаснее переносить.", "Удаляйте старую папку только после проверки открытия прежнего JSON, расчёта и экспорта в новой версии."],
["Close the application and back up the user data directory. A typical Windows path is %USERPROFILE%\\.trajectory_lab.", "Extract the new version separately and test it before deleting the previous one. Do not overwrite a running application.", "Transfer only required user models. Review .py source before copying; JSON/CSV tables are easier and safer to migrate.", "Delete the old folder only after verifying old JSON loading, calculation and export in the new version."],
[("Backup", "Скопировать .trajectory_lab."),("Update", "Распаковать приложение отдельно."),("Cleanup", "Удалять старую папку после проверки.")],
[("Backup", "Copy .trajectory_lab."),("Update", "Extract the application separately."),("Cleanup", "Remove the old folder after validation.")],
"Не удаляйте пользовательский каталог при обновлении: там могут храниться ваши модели и настройки.",
"Do not delete the user data folder during an update; it may contain your models and settings."),
("Финальный чек-лист", "Final acceptance checklist",
"Перед использованием результата проверяйте не только наличие красивого графика, но и правильность постановки, размерностей, применимости модели и сходимости.",
"Before accepting a result, check more than a visually pleasing plot: verify the setup, dimensions, model applicability and convergence.",
["Сверьте массу, диаметр, положение, скорость, гравитацию, ветер, атмосферу, drag-модель и максимальное время.", "Убедитесь, что единицы корректны, а предупреждения о применимости учтены. Для RK4 проверьте чувствительность к шагу; для DOP853 сохраните rtol и atol.", "Проверьте правую панель, графики и таблицу. Для ключевых величин сравните численные значения, а не только визуальную форму.", "Сохраните входной JSON, результат JSON, CSV и PDF. Перед обменом убедитесь, что файлы не содержат приватных путей или имён."],
["Review mass, diameter, position, velocity, gravity, wind, atmosphere, drag model and maximum time.", "Confirm units and account for applicability warnings. For RK4 test step sensitivity; for DOP853 record rtol and atol.", "Inspect results dock, plots and table. Compare numerical values for key quantities, not only visual shape.", "Save input JSON, result JSON, CSV and PDF. Before sharing, ensure files contain no private paths or names."],
[("Наука", "Эталон и применимость модели."),("Числа", "Допуски и сходимость."),("Документы", "JSON, CSV, PDF и очищенный журнал.")],
[("Science", "Reference case and model validity."),("Numbers", "Tolerances and convergence."),("Records", "JSON, CSV, PDF and sanitized journal.")],
"Если сомневаетесь в применимости корреляции, укажите это в отчёте и не выдавайте результат за универсальный прогноз.",
"If model applicability is uncertain, state it in the report and do not present the result as a universal prediction."),
]

from xml.sax.saxutils import escape
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import KeepTogether

NAVY = HexColor("#1f4e79")
INK = HexColor("#263238")
MUTED = HexColor("#61717b")
GRID = HexColor("#cbd3d9")
PALE = HexColor("#eef2f5")
WHITE = colors.white

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(
    name="TLTitle", fontName="TL-Bold", fontSize=16, leading=19,
    textColor=NAVY, spaceAfter=7, alignment=TA_LEFT,
))
styles.add(ParagraphStyle(
    name="TLLead", fontName="TL-Bold", fontSize=9.4, leading=13,
    textColor=INK, spaceAfter=8,
))
styles.add(ParagraphStyle(
    name="TLBody", fontName="TL-Regular", fontSize=8.3, leading=11.2,
    textColor=INK, spaceAfter=6,
))
styles.add(ParagraphStyle(
    name="TLTableHead", fontName="TL-Bold", fontSize=7.3, leading=9,
    textColor=WHITE,
))
styles.add(ParagraphStyle(
    name="TLTable", fontName="TL-Regular", fontSize=7.2, leading=9.2,
    textColor=INK,
))
styles.add(ParagraphStyle(
    name="TLTableStrong", fontName="TL-Bold", fontSize=7.2, leading=9.2,
    textColor=INK,
))
styles.add(ParagraphStyle(
    name="TLNote", fontName="TL-Regular", fontSize=7.8, leading=10.5,
    textColor=NAVY,
))
styles.add(ParagraphStyle(
    name="TLCoverTitle", fontName="TL-Bold", fontSize=28, leading=33,
    textColor=NAVY, spaceAfter=8,
))
styles.add(ParagraphStyle(
    name="TLCoverSub", fontName="TL-Regular", fontSize=13, leading=18,
    textColor=INK,
))
styles.add(ParagraphStyle(
    name="TLContents", fontName="TL-Regular", fontSize=8.0, leading=10.4,
    textColor=INK,
))


def para(text: str, style: str = "TLBody") -> Paragraph:
    return Paragraph(escape(str(text)), styles[style])


def draw_page(canvas, doc):
    canvas.saveState()
    width, height = A4
    page = canvas.getPageNumber()
    canvas.setStrokeColor(GRID)
    canvas.setLineWidth(0.45)
    canvas.line(17 * mm, 15 * mm, width - 17 * mm, 15 * mm)
    canvas.setFont("TL-Regular", 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(17 * mm, 10 * mm, f"TrajectoryLab {RELEASE}  |  Scientific user manual")
    canvas.drawRightString(width - 17 * mm, 10 * mm, str(page))
    canvas.restoreState()


def make_cover(language: str):
    if language == "ru":
        title = "Руководство пользователя"
        subtitle = "Научная среда для моделирования движения сферических объектов"
        lines = [
            "Версия документа: TrajectoryLab 0.4.2",
            "Интерфейс: русский и английский",
            "Платформа: Windows 10/11 x64",
            "Стек: Python · PySide6 · Qt 6 · pyqtgraph · Pint · SciPy",
            "Область: низкоскоростные лабораторные и спортивные эксперименты",
            "Модель: материальная точка / жёсткая сфера, поступательное движение",
            "Подготовлено для локального научного использования",
        ]
        caution = "Документ описывает функции, предусмотренные в исходном проекте. Фактическое поведение конкретной сборки зависит от её комплектации и версии."
        language_label = "РУССКАЯ РЕДАКЦИЯ"
    else:
        title = "User Manual"
        subtitle = "Scientific environment for modelling the motion of spherical objects"
        lines = [
            "Document version: TrajectoryLab 0.4.2",
            "Interface languages: Russian and English",
            "Platform: Windows 10/11 x64",
            "Stack: Python · PySide6 · Qt 6 · pyqtgraph · Pint · SciPy",
            "Scope: low-speed laboratory and sports experiments",
            "Model: point mass / rigid sphere, translational motion",
            "Prepared for local scientific use",
        ]
        caution = "This manual describes features provided by the source project. Actual behaviour depends on the installed build and its version."
        language_label = "ENGLISH EDITION"
    story = [Spacer(1, 26 * mm), para("TRAJECTORYLAB", "TLCoverTitle"), para(title, "TLCoverSub"), Spacer(1, 7 * mm)]
    story.append(para(subtitle, "TLLead"))
    story.append(Spacer(1, 7 * mm))
    story.append(Table([[para(language_label, "TLTableHead")]], colWidths=[176 * mm], style=TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), NAVY), ("LEFTPADDING", (0,0),(-1,-1), 9),
        ("RIGHTPADDING", (0,0),(-1,-1), 9), ("TOPPADDING", (0,0),(-1,-1), 7),
        ("BOTTOMPADDING", (0,0),(-1,-1), 7),
    ])))
    story.append(Spacer(1, 12 * mm))
    for line in lines:
        story.append(para("• " + line, "TLBody"))
    story.append(Spacer(1, 10 * mm))
    story.append(para(caution, "TLNote"))
    story.append(Spacer(1, 25 * mm))
    story.append(para("TrajectoryLab · pomidorkmen", "TLLead"))
    story.append(PageBreak())
    return story


def make_contents(language: str):
    heading = "Содержание" if language == "ru" else "Contents"
    story = [para(heading, "TLTitle"), Spacer(1, 2 * mm)]
    rows = []
    for index, page in enumerate(PAGES, 1):
        name = page[0] if language == "ru" else page[1]
        rows.append([para(f"{index:02d}", "TLTableStrong"), para(name, "TLContents")])
    table = Table(rows, colWidths=[12 * mm, 164 * mm], repeatRows=0)
    table.setStyle(TableStyle([
        ("VALIGN", (0,0),(-1,-1),"MIDDLE"),
        ("LINEBELOW", (0,0),(-1,-1), 0.25, GRID),
        ("LEFTPADDING", (0,0),(-1,-1), 4), ("RIGHTPADDING", (0,0),(-1,-1), 4),
        ("TOPPADDING", (0,0),(-1,-1), 2.2), ("BOTTOMPADDING", (0,0),(-1,-1), 2.2),
        ("TEXTCOLOR", (0,0),(0,-1), NAVY),
    ]))
    story.extend([table, PageBreak()])
    return story


def make_chapter(page: tuple, language: str):
    title_i, lead_i, body_i, rows_i, note_i = (0,2,4,6,8) if language == "ru" else (1,3,5,7,9)
    story = [para(page[title_i], "TLTitle"), para(page[lead_i], "TLLead")]
    for paragraph in page[body_i]:
        story.append(para(paragraph, "TLBody"))
    rows = [[para("Элемент / действие", "TLTableHead"), para("Описание", "TLTableHead")]] if language == "ru" else [[para("Control / action", "TLTableHead"), para("Description", "TLTableHead")]]
    for left, right in page[rows_i]:
        rows.append([para(left, "TLTableStrong"), para(right, "TLTable")])
    table = Table(rows, colWidths=[43 * mm, 133 * mm], repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,0), NAVY), ("GRID", (0,0),(-1,-1), 0.35, GRID),
        ("VALIGN", (0,0),(-1,-1),"TOP"),
        ("LEFTPADDING", (0,0),(-1,-1), 5), ("RIGHTPADDING", (0,0),(-1,-1), 5),
        ("TOPPADDING", (0,0),(-1,-1), 4), ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ("ROWBACKGROUNDS", (0,1),(-1,-1), [WHITE, PALE]),
    ]))
    story.extend([Spacer(1, 2 * mm), table, Spacer(1, 4 * mm)])
    note_title = "Практическое замечание" if language == "ru" else "Practical note"
    note = Table([[para(note_title, "TLTableStrong")], [para(page[note_i], "TLNote")]], colWidths=[176 * mm])
    note.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,0), PALE), ("BOX", (0,0),(-1,-1), 0.5, GRID),
        ("LINEBELOW", (0,0),(-1,0), 0.3, GRID),
        ("LEFTPADDING", (0,0),(-1,-1), 7), ("RIGHTPADDING", (0,0),(-1,-1), 7),
        ("TOPPADDING", (0,0),(-1,-1), 5), ("BOTTOMPADDING", (0,0),(-1,-1), 5),
    ]))
    story.extend([note, PageBreak()])
    return story


def build_manual(language: str) -> Path:
    filename = "TrajectoryLab_Manual_RU.pdf" if language == "ru" else "TrajectoryLab_Manual_EN.pdf"
    path = OUT / filename
    doc = SimpleDocTemplate(
        str(path), pagesize=A4, rightMargin=17*mm, leftMargin=17*mm,
        topMargin=17*mm, bottomMargin=21*mm,
        title=("TrajectoryLab — Руководство пользователя" if language == "ru" else "TrajectoryLab — User Manual"),
        author="TrajectoryLab Project",
        subject="Scientific desktop application user guide",
    )
    story = make_cover(language) + make_contents(language)
    for chapter in PAGES:
        story.extend(make_chapter(chapter, language))
    doc.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
    return path


if __name__ == "__main__":
    for lang in ("ru", "en"):
        result = build_manual(lang)
        print(f"Generated {result}")
