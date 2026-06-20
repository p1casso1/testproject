# Примеры запросов через curl

## 1. Health check
```bash
curl -X GET http://localhost:8000/api/health
```

## 2. Metrics
```bash
curl -X GET http://localhost:8000/api/metrics
```

## 3. Успешная отправка формы обратной связи
```bash
curl -X POST http://localhost:8000/api/contact \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Иван Иванов",
    "phone": "+998901234567",
    "email": "ivan@example.com",
    "comment": "Здравствуйте! Хочу обсудить разработку backend для моего стартапа."
  }'
```

## 4. Ошибка валидации (невалидный email) -> 422
```bash
curl -X POST http://localhost:8000/api/contact \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Иван",
    "phone": "+998901234567",
    "email": "not-an-email",
    "comment": "Тестовое сообщение"
  }'
```

## 5. Негативный комментарий (проверка AI sentiment)
```bash
curl -X POST http://localhost:8000/api/contact \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Пётр Петров",
    "phone": "+998901112233",
    "email": "petr@example.com",
    "comment": "Это ужасно, сайт не работает уже неделю, я очень недоволен!"
  }'
```

## 6. Rate limiting (выполните 6 раз подряд с лимитом 5/час по умолчанию)
```bash
for i in {1..6}; do
  curl -s -o /dev/null -w "Запрос $i -> HTTP %{http_code}\n" \
    -X POST http://localhost:8000/api/contact \
    -H "Content-Type: application/json" \
    -d '{
      "name": "Тест Тестов",
      "phone": "+998900000000",
      "email": "test@example.com",
      "comment": "Проверка rate limiting"
    }'
done
```
