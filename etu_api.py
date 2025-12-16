
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ETUApiClient:
    def __init__(self):
        self.base_url = "https://digital.etu.ru/api/mobile"
        self.groups_cache = None
        self.schedule_cache = {}
        self.cache_time = None
        self.cache_duration = timedelta(hours=6)
        self.day_names = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

    def fetch_all_groups(self) -> Optional[List[Dict]]:

        try:
            
            if self.groups_cache and self.cache_time:
                if datetime.now() - self.cache_time < self.cache_duration:
                    logger.info("Используем кэшированные данные групп")
                    return self.groups_cache

            response = requests.get(f"{self.base_url}/groups", timeout=15)
            response.raise_for_status()
            self.groups_cache = response.json()
            self.cache_time = datetime.now()
            logger.info(f"Загружено групп: {len(self.groups_cache)}")
            return self.groups_cache
        except Exception as e:
            logger.error(f"Ошибка при загрузке списка групп: {e}")
            return None

    def find_group_info(self, group_number: str) -> Optional[Dict]:
        """Находим полную информацию о группе"""
        all_groups = self.fetch_all_groups()
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

    def fetch_complete_schedule(self) -> Optional[Dict]:
        """Загружаем полное расписание для всех групп"""
        # Начинаем с понедельника текущей недели
        today = datetime.now().date()
        monday = today - timedelta(days=today.weekday())
        cache_key = monday.strftime('%Y-%m-%d')

        # Проверяем кэш
        if cache_key in self.schedule_cache:
            logger.info(f"Используем кэшированное расписание для {cache_key}")
            return self.schedule_cache[cache_key]

        try:
            end_date = monday + timedelta(days=6)  # Воскресенье

            params = {
                'from': monday.strftime('%Y-%m-%d'),
                'to': end_date.strftime('%Y-%m-%d')
            }

            logger.info("Загружаю полное расписание...")
            response = requests.get(
                f"{self.base_url}/schedule",
                params=params,
                timeout=30
            )

            if response.status_code != 200:
                logger.error(f"Ошибка API: {response.status_code}")
                return None

            schedule_data = response.json()
            self.schedule_cache[cache_key] = schedule_data
            logger.info(f"Загружено расписание для {len(schedule_data)} групп")
            return schedule_data

        except Exception as e:
            logger.error(f"Ошибка при загрузке расписания: {e}")
            return None

    def extract_group_schedule(self, group_number: str) -> Optional[Dict]:
        """Извлекаем расписание для конкретной группы"""
        full_schedule = self.fetch_complete_schedule()
        if not full_schedule or group_number not in full_schedule:
            logger.warning(f"Расписание для группы {group_number} не найдено")
            return None
        return full_schedule[group_number]

    def remove_duplicate_lessons(self, lessons: List[Dict]) -> List[Dict]:
        """Удаляет дублирующиеся пары из списка занятий"""
        if not lessons:
            return []

        seen_combinations = {}
        unique_lessons = []

        for lesson in lessons:
            time_start = lesson.get('start_time', '')
            time_end = lesson.get('end_time', '')
            subject = lesson.get('name', '')
            teacher = lesson.get('teacher', '')
            classroom = lesson.get('room', '')

            key = f"{time_start}|{time_end}|{subject}|{teacher}|{classroom}"

            if key not in seen_combinations:
                seen_combinations[key] = True
                unique_lessons.append(lesson)

        return unique_lessons

    def get_today_schedule(self, group_number: str) -> Optional[str]:
        """Получает расписание на сегодня"""
        group_schedule = self.extract_group_schedule(group_number)
        if not group_schedule:
            return None

        days_data = group_schedule.get('days', {})
        today_key = str(datetime.now().weekday())  # 0 для понедельника и т.д.

        if today_key not in days_data:
            current_weekday = datetime.now().weekday()
            day_name = self.day_names[current_weekday]
            return f"На {day_name.lower()} пар нет 🎉"

        day_data = days_data[today_key]
        lessons = self.remove_duplicate_lessons(day_data.get('lessons', []))

        if not lessons:
            current_weekday = datetime.now().weekday()
            day_name = self.day_names[current_weekday]
            return f"На {day_name.lower()} пар нет 🎉"

        current_weekday = datetime.now().weekday()
        day_name = self.day_names[current_weekday]
        return self.format_day_schedule(lessons, day_name)

    def get_tomorrow_schedule(self, group_number: str) -> Optional[str]:
        """Получает расписание на завтра"""
        group_schedule = self.extract_group_schedule(group_number)
        if not group_schedule:
            return None

        days_data = group_schedule.get('days', {})
        tomorrow_key = str((datetime.now().weekday() + 1) % 7)  # Ключ для завтрашнего дня

        if tomorrow_key not in days_data:
            current_weekday = datetime.now().weekday()
            tomorrow_weekday = (current_weekday + 1) % 7
            day_name = self.day_names[tomorrow_weekday]
            return f"На {day_name.lower()} пар нет 🎉"

        day_data = days_data[tomorrow_key]
        lessons = self.remove_duplicate_lessons(day_data.get('lessons', []))

        if not lessons:
            current_weekday = datetime.now().weekday()
            tomorrow_weekday = (current_weekday + 1) % 7
            day_name = self.day_names[tomorrow_weekday]
            return f"На {day_name.lower()} пар нет 🎉"

        current_weekday = datetime.now().weekday()
        tomorrow_weekday = (current_weekday + 1) % 7
        day_name = self.day_names[tomorrow_weekday]
        return self.format_day_schedule(lessons, day_name)

    def get_week_schedule(self, group_number: str) -> Optional[List[str]]:
        """Получает расписание на неделю"""
        group_schedule = self.extract_group_schedule(group_number)
        if not group_schedule:
            return None

        days_data = group_schedule.get('days', {})

        if not days_data:
            return ["На эту неделю пар нет 🎉"]

        result = []

        for i in range(7):
            day_key = str(i)
            if day_key in days_data:
                day_data = days_data[day_key]
                lessons = self.remove_duplicate_lessons(day_data.get('lessons', []))

                if lessons:
                    day_name = self.day_names[i]
                    day_schedule = self.format_day_schedule(lessons, day_name)
                    result.append(day_schedule)

        if not result:
            return ["На эту неделю пар нет 🎉"]

        return result

    def get_next_lesson(self, group_number: str) -> Optional[str]:
        """Получает ближайшую пару"""
        group_schedule = self.extract_group_schedule(group_number)
        if not group_schedule:
            return None

        days_data = group_schedule.get('days', {})
        today_key = str(datetime.now().weekday())

        if today_key not in days_data:
            current_weekday = datetime.now().weekday()
            day_name = self.day_names[current_weekday]
            return f"На {day_name.lower()} пар нет 🎉"

        day_data = days_data[today_key]
        lessons = day_data.get('lessons', [])

        if not lessons:
            current_weekday = datetime.now().weekday()
            day_name = self.day_names[current_weekday]
            return f"На {day_name.lower()} пар нет 🎉"

        now = datetime.now()
        next_lesson = None

        for lesson in lessons:
            time_str = lesson.get('start_time', '')
            if not time_str:
                continue

            try:
                lesson_time = datetime.strptime(time_str, '%H:%M').time()
                lesson_datetime = datetime.combine(now.date(), lesson_time)

                if lesson_datetime > now:
                    if next_lesson is None or lesson_datetime < next_lesson['time']:
                        next_lesson = {
                            'time': lesson_datetime,
                            'data': lesson
                        }
            except ValueError:
                continue

        if not next_lesson:
            current_weekday = datetime.now().weekday()
            day_name = self.day_names[current_weekday]
            return f"На {day_name.lower()} больше пар нет 🎉"

        return self.format_single_lesson(next_lesson['data'])

    def format_day_schedule(self, lessons: List[Dict], day_name: str) -> str:
        """Форматирует расписание на один день"""
        lessons_sorted = sorted(
            lessons,
            key=lambda x: x.get('start_time', '') or '99:99'
        )

        result = f"📅 <b>{day_name}</b>\n"
        result += "─" * 30 + "\n\n"

        for i, lesson in enumerate(lessons_sorted, 1):
            time_start = lesson.get('start_time', '')
            time_end = lesson.get('end_time', '')
            subject = lesson.get('name', 'Неизвестный предмет')
            lesson_type = lesson.get('subjectType', '')
            teacher = lesson.get('teacher', '')
            classroom = lesson.get('room', '')

            type_display = ""
            if lesson_type:
                type_map = {
                    'Лек': 'Лекция',
                    'Пр': 'Практика',
                    'Лаб': 'Лабораторная',
                    'Сем': 'Семинар'
                }
                type_display = type_map.get(lesson_type, lesson_type)

            time_display = f"{time_start}–{time_end}" if time_start and time_end else "Время не указано"

            result += f"<b>#{i} 🕐 {time_display}</b>\n"
            result += f"   📚 {subject}\n"

            if type_display:
                result += f"   📝 {type_display}\n"

            if teacher:
                result += f"   👨‍🏫 {teacher}\n"

            if classroom:
                result += f"   🏫 {classroom}\n"
            else:
                result += f"   🏫 Аудитория не указана\n"

            result += "\n"

        return result

    def format_single_lesson(self, lesson: Dict) -> str:
        """Форматирует одну пару"""
        time_start = lesson.get('start_time', '')
        time_end = lesson.get('end_time', '')
        subject = lesson.get('name', 'Неизвестный предмет')
        lesson_type = lesson.get('subjectType', '')
        teacher = lesson.get('teacher', '')
        classroom = lesson.get('room', '')

        type_display = ""
        if lesson_type:
            type_map = {
                'Лек': 'Лекция',
                'Пр': 'Практика',
                'Лаб': 'Лабораторная',
                'Сем': 'Семинар'
            }
            type_display = type_map.get(lesson_type, lesson_type)

        time_display = f"{time_start}–{time_end}" if time_start and time_end else "Время не указано"

        result = "⏱ <b>Ближайшая пара:</b>\n"
        result += "─" * 30 + "\n\n"
        result += f"🕐 <b>{time_display}</b>\n"
        result += f"📚 {subject}\n"

        if type_display:
            result += f"📝 {type_display}\n"

        if teacher:
            result += f"👨‍🏫 {teacher}\n"

        if classroom:
            result += f"🏫 {classroom}\n"
        else:
            result += f"🏫 Аудитория не указана\n"

        if time_start:
            try:
                now = datetime.now()
                lesson_time = datetime.strptime(time_start, '%H:%M').time()
                lesson_datetime = datetime.combine(now.date(), lesson_time)

                if lesson_datetime > now:
                    time_diff = lesson_datetime - now
                    hours = time_diff.seconds // 3600
                    minutes = (time_diff.seconds % 3600) // 60

                    if hours > 0:
                        result += f"\n⏳ До пары: {hours} ч {minutes} мин"
                    else:
                        result += f"\n⏳ До пары: {minutes} мин"
            except:
                pass

        return result
api_client = ETUApiClient()