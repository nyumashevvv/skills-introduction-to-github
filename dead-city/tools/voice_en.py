"""English voice-over script: what each (Russian) subtitle line is said as. Keys are the exact Russian texts
from the chapter scenes and tools/story_text.py; tools/gen_voice.py fails on any line missing here."""

EN = {
    # chapter 1
    '…если кто-то слышит — эвакуация со стадиона «Динамо» на рассвете. Повторяю: стадион, на рассвете.':
        '...if anyone can hear this, evacuation from Dynamo stadium at dawn. I repeat: the stadium, at dawn.',
    'Ты меня слышишь? Хорошо. Через центр не пройти — иди по Садовой к полицейскому участку. Там оружейная, она тебе понадобится.':
        "You can hear me? Good. You won't get through downtown. Take Garden Street to the police station. "
        "There's an armory there. You'll need it.",
    'Совет: нож бьёт бесшумно. Выстрелы слышно на весь квартал — мертвецы сбегутся.':
        'A tip: the knife is silent. Gunshots carry across the whole block, and the dead will come running.',
    'Автомат? Отличная находка. Только… слышишь? Они лезут из переулков!':
        "A rifle? Nice find. But wait... do you hear that? They're coming out of the alleys!",
    'Тихо? Двигай дальше, участок сразу за автобусом.':
        "All quiet? Keep moving. The station is just past the bus.",
    'Автобус перегородил всю улицу. Обойди: магазин слева сквозной, выход во двор через подсобку. '
    'Или переулком — двор выводит обратно на улицу.':
        "A bus is blocking the whole street. Go around. The shop on the left goes straight through, out the back "
        "into the yard. Or take the alley. The yard leads back to the street.",
    'Сзади! Целая толпа — беги к участку!': "Behind you! A whole crowd! Run for the station!",
    'У входа в участок… повар с тесаком? Он не человек уже. Осторожно, он бросается с разбега — отходи в сторону, '
    'а если врежется в стену, бей!':
        "At the station door... a cook with a cleaver? He's not human anymore. Careful, he charges. Step aside, "
        "and when he hits the wall, let him have it!",
    'Готов! Заходи в участок, пока толпа не догнала.': "He's down! Get inside before the crowd catches up.",
    # chapter 2
    'Ты внутри? Хорошо. Оружейная в конце коридора, но она под ключ-картой. Проверь кабинет начальника — первая дверь слева.':
        "You're inside? Good. The armory is at the end of the corridor, but it needs a key card. "
        "Check the chief's office, first door on the left.",
    'И включи фонарик — клавиша F. Там темно, как в могиле.': "And turn on your flashlight, the F key. It's dark as a grave in there.",
    'Карта у тебя? Отлично, теперь в оружейную.': "Got the card? Great. Now, the armory.",
    'Бери всё, что унесёшь.': "Take everything you can carry.",
    'Чёрт, это сигнализация! Замки камер открылись! Уходи через гараж — ворота в восточной стене!':
        "Damn, that's the alarm! The cell locks are open! Get out through the garage, the gate is in the east wall!",
    'Во дворе машина… и это Боболев со щитом! Щит держит пули — целься в голову, заходи сбоку или стреляй из РПГ.':
        "There's a car in the yard... and that's Bobolev with a riot shield! The shield stops bullets. Aim for the head, "
        "flank him, or use the rocket launcher.",
    'Чисто! Машина ждёт — давай!': "Clear! The car is waiting. Go!",
    # chapter 3 (mall)
    'Машина встала? Через улицу не пройти — там баррикада. Иди через «Галактику»: с крыши парковки пандус спускается '
    'прямо к больнице.':
        "The car's dead? You can't get down the street, there's a barricade. Go through the Galaktika mall. "
        "From the roof car park, a ramp goes straight down to the hospital.",
    'Темно… эскалаторы стоят, решётка на третий этаж без питания. Генераторная на первом этаже, в восточном крыле, '
    'в самом конце, за игрушками. Запусти генератор.':
        "It's dark... the escalators are dead, and the shutter to the third floor has no power. The generator room is "
        "on the ground floor, east wing, at the very end, past the toy store. Start the generator.",
    'Есть свет! Решётка у эскалатора на третий этаж поднята. Кинотеатр наверху — оттуда лестница на крышу. '
    'И… на фуд-корте кто-то зашевелился.':
        "Lights are on! The shutter to the third floor is up. The cinema is at the top, the stairs to the roof are "
        "there. And... something is moving in the food court.",
    'В зале кто-то есть… Это ростовая кукла? Заяц Гоша из детской комнаты. Внутри костюма давно не аниматор. '
    'Он прыгает с разбега — уходи в сторону!':
        "Someone's in the hall... is that a mascot? Gosha the Bunny, from the kids' room. Whatever is inside that "
        "costume, it's not an entertainer anymore. He leaps at you. Dodge to the side!",
    'Готов! Дверь на крышу — справа от кинозала. Поднимайся!': "Got him! The roof door is to the right of the cinema. Go up!",
    'Ты на крыше. Выезд у западного края: пандус спускается в переулок, там ворота к больнице. Беги!':
        "You're on the roof. The exit is on the west side: the ramp goes down into the alley, and the gate there "
        "leads to the hospital. Run!",
    # chapter 4 (hospital)
    'Больница? Плохо, но другого пути нет. Пожарный выход в западном крыле на электрозамке — сначала запусти генератор, '
    'он в техническом крыле, на востоке.':
        "The hospital? Not good, but there's no other way. The fire exit in the west wing has an electric lock. "
        "Start the generator first. It's in the technical wing, to the east.",
    'Свет отключён. Фонарик — F. И лишний раз не шуми.': "The power is out. Flashlight, F. And keep the noise down.",
    'Дробовик охраны! В тесных коридорах лучше не придумаешь. Клавиша 4.':
        "The guard's shotgun! Nothing better in tight corridors. Key four.",
    'Есть питание! Чёрт… сирена подняла всё здание. Пожарная дверь открыта — беги!':
        "Power's back! Damn... the siren woke up the whole building. The fire door is open. Run!",
    'Во дворе… оно светится?! Это нулевой пациент, с него всё началось. Не попадай под его плевки и не дай ему созвать больных!':
        "In the yard... is that thing glowing? That's patient zero. This all started with him. Stay out of his spit, "
        "and don't let him call the others!",
    'Он мёртв. Вход в метро в углу двора — иди!': "He's dead. The metro entrance is in the corner of the yard. Go!",
    # chapter 5 (subway)
    'Ты в метро? До «Динамо» два перегона. Иди по левому пути — правый тоннель завалило.':
        "You're in the metro? Two stops to Dynamo. Take the left track. The right tunnel has caved in.",
    'Впереди сошедший вагон, тоннель перекрыт. Ищи служебную дверь — они есть через каждые сто метров.':
        "There's a derailed car ahead, the tunnel is blocked. Look for a service door. There's one every hundred meters.",
    'Слышишь топот? Сзади бегуны — не останавливайся!': "Hear those footsteps? Runners behind you. Don't stop!",
    'Выход перекрыт решёткой. Взламываю систему станции — продержись минуту!':
        "The exit is barred by a gate. I'm hacking the station system. Hold out for a minute!",
    'По боковому проходу идёт что-то тяжёлое… Обходчик с кувалдой! Когда он бьёт по земле — подпрыгни, ударная волна идёт по полу.':
        "Something heavy is coming down the side passage... a track worker with a sledgehammer! When he slams the "
        "ground, jump. The shockwave runs along the floor.",
    'Есть! Решётка поднята — наверх, стадион прямо над тобой!': "Got it! The gate is up. Go up, the stadium is right above you!",
    # chapter 6 (stadium)
    'Ты на стадионе? Вертолёт на подходе. Площадка в центре поля — жди там.':
        "You're at the stadium? The helicopter is on its way. The landing pad is in the middle of the field. Wait there.",
    'Борт-двенадцать на связи. Вижу площадку, но вокруг толпа — сесть не могу! Продержись две минуты, я сделаю круг.':
        "Twelve here. I see the pad, but there's a crowd all around it. I can't land! Hold out for two minutes, "
        "I'll circle around.",
    'С севера идёт что-то огромное… Это Алёна! Она швыряет обломки и бьёт о землю — прыгай, когда замахивается. '
    'Пока она жива, вертолёт не сядет!':
        "Something huge is coming from the north... It's Alyona! She throws debris and slams the ground. "
        "Jump when she winds up. The helicopter can't land while she's alive!",
    'Захожу на посадку! Держись, я почти над тобой!': "Coming in to land! Hang on, I'm almost on top of you!",
    'Сел! Запрыгивай, живо!': "I'm down! Get in, now!",
    # intro cutscene
    'Экстренный выпуск. Власти просят жителей не покидать дома и не открывать двери незнакомым. '
    'Число заболевших растёт с каждым часом.':
        "Breaking news. Authorities urge residents to stay at home and not to open the door to strangers. "
        "The number of infected is growing by the hour.",
    'Девять дней назад это передавали по всем каналам. Говорили — новый грипп. Через сутки больницы были переполнены.':
        "Nine days ago, that was on every channel. They said it was a new flu. A day later, the hospitals were full.",
    'Через двое суток город пал. Мёртвые поднимались и шли за живыми. Армия ушла первой.':
        "Two days later, the city fell. The dead got up and came for the living. The army was the first to leave.",
    'Я спрятался в подвале своего дома. Девять дней тишины, консервы и старая рация. Вчера кончилась еда.':
        "I hid in the basement of my building. Nine days of silence, canned food, and an old radio. "
        "Yesterday, the food ran out.",
    'Стадион на другом конце города. Но другого шанса не будет. Пора выходить.':
        "The stadium is on the other side of the city. But there won't be another chance. Time to go.",
    # ending cutscene
    'Держись крепче! Взлетаем!': "Hold on tight! We're lifting off!",
    'Стадион уходил вниз. Мёртвые тянули к нам руки, будто ещё могли достать.':
        "The stadium fell away below us. The dead reached up at us, as if they could still get us.",
    'Борт-двенадцать, вижу вас. Коридор чистый, курс на базу. Добро пожаловать в живые.':
        "Twelve, I have you on radar. The corridor is clear, head for the base. Welcome back to the living.",
    'Девять дней я ждал рассвета. Город остался позади. Где-то там ещё есть люди — и теперь я снова один из них.':
        "Nine days I waited for the dawn. The city is behind me now. There are still people out there, "
        "and now I'm one of them again.",
}
