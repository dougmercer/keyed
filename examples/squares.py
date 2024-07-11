from keyed import Rectangle, Scene

s = Scene(freehand=True)

length = 400

for n in range(0, 20):
    for m in range(0, 20):
        if (n + m) % 2 == 0:
            continue
        r = Rectangle(s, length, length, x=n * length, y=m * length)
        s.add(r)

# for n in range(0, 20):
#     for m in range(0, 20):
#         if (n+m) % 2 == 0:
#             continue
#         r = Rectangle(s, length, length, x=0, y=0, alpha=0.01).center()
#         s.add(r)
s.preview()
