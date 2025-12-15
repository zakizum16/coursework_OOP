import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional


def fetch_all_groups() -> Optional[List[Dict]]:
    """Получаем все группы с API"""
    try:
        response = requests.get(
            "https://digital.etu.ru/api/mobile/groups",
            timeout=15
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Ошибка при загрузке списка групп: {e}")
        return None


def find_group_info(all_groups: List[Dict], group_number: str) -> Optional[Dict]:
    """Находим полную информацию о группе"""
    if not all_groups:
        return None

    for faculty in all_groups:
        for department in faculty.get('departments', []):
            for group in department.get('groups', []):
                if group.get('number') == group_number:
                    return {
                        'id': group['id'],
                        'number': group['number'],
                        'course': group['course'],
                        'studyingType': group.get('studyingType', ''),
                        'educationLevel': group.get('educationLevel', ''),
                        'faculty': faculty['title'],
                        'department': department['title']
                    }
    return None


def fetch_complete_schedule() -> Optional[Dict]:
    """Загружаем полное расписание для всех групп"""
    try:
        today = datetime.now().date()
        end_date = today + timedelta(days=7)

        params = {
            'from': today.strftime('%Y-%m-%d'),
            'to': end_date.strftime('%Y-%m-%d')
        }

        print(f"📡 Загружаю полное расписание...")
        response = requests.get(
            "https://digital.etu.ru/api/mobile/schedule",
            params=params,
            timeout=30
        )

        if response.status_code != 200:
            print(f"❌ Ошибка API: {response.status_code}")
            return None

        return response.json()

    except Exception as e:
        print(f"❌ Ошибка при загрузке расписания: {e}")
        return None


def extract_group_schedule(full_schedule: Dict, group_number: str) -> Optional[Dict]:
    """Извлекаем расписание для конкретной группы"""
    if not full_schedule or group_number not in full_schedule:
        print(f"❌ Расписание для группы {group_number} не найдено")
        return None
    return full_schedule[group_number]


def format_time_range(time_start: str, time_end: str) -> str:
    """Форматирует временной диапазон"""
    if time_start and time_end:
        return f"{time_start}–{time_end}"
    elif time_start:
        return f"{time_start}"
    else:
        return "Время не указано"


def get_day_name(day_number: int) -> str:
    """Возвращает название дня недели"""
    days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    today = datetime.now().date()
    target_date = today + timedelta(days=day_number)
    day_of_week = target_date.weekday()  # 0=понедельник, 6=воскресенье
    return days[day_of_week]


def get_formatted_date(day_number: int) -> str:
    """Возвращает отформатированную дату"""
    today = datetime.now().date()
    target_date = today + timedelta(days=day_number)
    return target_date.strftime("%d.%m.%Y")


def remove_duplicate_lessons(lessons: List[Dict]) -> List[Dict]:
    """Удаляет дублирующиеся пары из списка занятий"""
    if not lessons:
        return []

    # Создаем словарь для отслеживания уникальных пар
    seen_combinations = {}
    unique_lessons = []

    for lesson in lessons:
        # Создаем ключ на основе основных атрибутов пары
        time_start = lesson.get('start_time', '')
        time_end = lesson.get('end_time', '')
        subject = lesson.get('name', '')
        teacher = lesson.get('teacher', '')
        classroom = lesson.get('room', '')

        # Ключ для сравнения (игнорируем подгруппы и вторых преподавателей)
        key = f"{time_start}|{time_end}|{subject}|{teacher}|{classroom}"

        # Если мы еще не видели такую комбинацию, добавляем её
        if key not in seen_combinations:
            seen_combinations[key] = True
            unique_lessons.append(lesson)
        else:
            # Это дубликат - можно его проигнорировать или добавить информацию о подгруппе
            # к существующей записи
            pass

    return unique_lessons
def print_beautiful_schedule(group_schedule: Dict, group_info: Dict):
    """Красиво выводим расписание для группы с обработкой дубликатов"""
    if not group_schedule:
        print("\n📭 Нет данных о расписании")
        return

    # Получаем дни из расписания
    days_data = group_schedule.get('days', {})

    if not days_data:
        print("📭 Нет запланированных занятий на этот период")
        return

    # Выводим заголовок
    print(f"\n{'⭐' * 30}")
    print(f"📅 РАСПИСАНИЕ ГРУППЫ {group_info['number']}")
    print(f"{'⭐' * 30}")
    print(f"👥 Факультет: {group_info['faculty']}")
    print(f"🏛 Кафедра: {group_info['department']}")
    print(f"🎓 Курс: {group_info['course']} | Форма: {group_info['studyingType']}")
    print(f"{'─' * 60}")

    total_unique_lessons = 0
    days_with_lessons = 0

    # Обрабатываем каждый день
    for day_key, day_data in days_data.items():
        try:
            day_number = int(day_key)
        except ValueError:
            continue

        lessons = day_data.get('lessons', [])

        if not lessons:
            continue

        # Фильтруем дубликаты
        unique_lessons = remove_duplicate_lessons(lessons)

        if not unique_lessons:
            continue

        days_with_lessons += 1
        total_unique_lessons += len(unique_lessons)

        # Получаем название дня и дату
        day_name = get_day_name(day_number)
        formatted_date = get_formatted_date(day_number)

        print(f"\n{'═' * 60}")
        print(f"📅 {day_name}, {formatted_date} (День {day_number + 1})")
        print(f"{'─' * 60}")

        # Сортируем уникальные пары по времени начала
        lessons_sorted = sorted(
            unique_lessons,
            key=lambda x: x.get('start_time', '') or '99:99'
        )

        for i, lesson in enumerate(lessons_sorted, 1):
            # Извлекаем данные из правильных ключей
            time_start = lesson.get('start_time', '')
            time_end = lesson.get('end_time', '')
            subject = lesson.get('name', 'Неизвестный предмет')
            lesson_type = lesson.get('subjectType', '')
            teacher = lesson.get('teacher', '')
            classroom = lesson.get('room', '')
            second_teacher = lesson.get('second_teacher', '')
            subgroup = lesson.get('subgroup', '')
            week = lesson.get('week', '')

            # Форматируем тип занятия
            type_display = ""
            if lesson_type:
                type_map = {
                    'Лек': 'Лекция',
                    'Пр': 'Практика',
                    'Лаб': 'Лабораторная',
                    'Сем': 'Семинар',
                    'Конс': 'Консультация',
                    'Зач': 'Зачет',
                    'Экз': 'Экзамен'
                }
                type_display = type_map.get(lesson_type, lesson_type)

            # Форматируем формат занятия
            form = lesson.get('form', '')
            form_display = ""
            if form:
                form_map = {
                    'online': 'Онлайн',
                    'offline': 'Очно',
                    'hybrid': 'Смешанный формат',
                    'standard': 'Стандартно',
                    'distant': 'Дистанционно'
                }
                form_display = form_map.get(form, form)

            # Вывод информации о паре
            print(f"\n#{i} 🕐 {format_time_range(time_start, time_end)}")
            print(f"   📚 {subject}")

            if type_display:
                print(f"   📝 {type_display}")

            # Информация о неделе
            if week and week != '0':
                print(f"   📆 Неделя: {week}")

            if teacher:
                print(f"   👨‍🏫 {teacher}")

            if second_teacher:
                print(f"   👨‍🏫 {second_teacher} (второй преподаватель)")

            # Информация о подгруппе
            if subgroup:
                print(f"   👥 Подгруппа: {subgroup}")

            if classroom:
                print(f"   🏫 Аудитория: {classroom}")
            else:
                print(f"   🏫 Аудитория не указана")

            if form_display:
                print(f"   💻 Формат: {form_display}")

    # Итоговая статистика
    print(f"\n{'═' * 60}")
    print(f"📊 ИТОГО:")
    print(f"   📅 Дней с занятиями: {days_with_lessons}")
    print(f"   📚 Всего уникальных пар: {total_unique_lessons}")

    if days_with_lessons > 0:
        average_per_day = total_unique_lessons / days_with_lessons
        print(f"   📈 Среднее пар в день: {average_per_day:.1f}")


def save_schedule_to_file(group_schedule: Dict, group_info: Dict, filename: str = None):
    """Сохраняет расписание в файл"""
    if not filename:
        filename = f"schedule_{group_info['number']}_{datetime.now().strftime('%Y%m%d')}.txt"

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            # Перехватываем вывод в файл
            import sys
            from io import StringIO

            old_stdout = sys.stdout
            sys.stdout = StringIO()

            print_beautiful_schedule(group_schedule, group_info)
            output = sys.stdout.getvalue()

            sys.stdout = old_stdout

            f.write(output)

        print(f"✅ Расписание сохранено в {filename}")
        return True
    except Exception as e:
        print(f"❌ Ошибка при сохранении файла: {e}")
        return False


def main():
    """Главная функция приложения"""
    print("=" * 60)
    print("📅 РАСПИСАНИЕ ЛЭТИ")
    print("=" * 60)

    while True:
        # Запрашиваем номер группы
        group_number = input("\n🔢 Введите номер группы (или 'выход' для завершения): ").strip()

        if group_number.lower() in ['выход', 'exit', 'quit', 'q']:
            print("\n👋 До свидания!")
            break

        if not group_number:
            print("❌ Пожалуйста, введите номер группы")
            continue

        # 1. Загружаем информацию о группах
        print("\n🔄 Загружаю информацию о группах...")
        all_groups = fetch_all_groups()

        if not all_groups:
            print("❌ Не удалось загрузить список групп")
            continue

        # 2. Ищем информацию о группе
        group_info = find_group_info(all_groups, group_number)

        if not group_info:
            print(f"❌ Группа '{group_number}' не найдена")
            print(f"💡 Попробуйте другой номер группы")
            continue

        print(f"✅ Найдена группа: {group_info['number']}")

        # 3. Загружаем полное расписание
        full_schedule = fetch_complete_schedule()

        if not full_schedule:
            print("❌ Не удалось загрузить расписание")
            continue

        print(f"✅ Загружено расписание для {len(full_schedule)} групп")

        # 4. Извлекаем расписание для нашей группы
        group_schedule = extract_group_schedule(full_schedule, group_number)

        if not group_schedule:
            print(f"❌ Не удалось найти расписание для группы {group_number}")
            print(f"💡 Попробуйте другую группу")
            continue

        # 5. Выводим красивое расписание
        print_beautiful_schedule(group_schedule, group_info)

        # 6. Предлагаем сохранить или продолжить
        print("\n" + "=" * 60)
        choice = input("💾 Сохранить расписание в файл? (да/нет/новая группа): ").strip().lower()

        if choice in ['да', 'yes', 'y', 'д']:
            filename = input(f"Введите имя файла (по умолчанию schedule_{group_number}.txt): ").strip()
            if not filename:
                filename = None
            save_schedule_to_file(group_schedule, group_info, filename)
        elif choice in ['новая группа', 'новая', 'new', 'n']:
            continue
        else:
            print("Продолжаем...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Программа завершена пользователем")
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
        import traceback

        traceback.print_exc()