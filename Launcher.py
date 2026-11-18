from multiprocessing import Process, Queue, freeze_support
import argparse

def main_task(q: Queue, path: str, theme: str):
    try:
        from main import TCWindow
        window = TCWindow(path, theme)
        window.mainloop()
    except TCWindow.LoadingDifferentVersionException as e:
        q.put(e.args[0])

if __name__ == "__main__":
    freeze_support()

    parser = argparse.ArgumentParser()
    parser.add_argument('file', type=str, help='Open scenario file', nargs='?', default='')
    parser.add_argument('--dark', help='Dark mode', nargs='?', default=False)
    parser.add_argument('--light', help='Light mode', nargs='?', default=False)
    args = parser.parse_args()
    if args.dark != False:
        theme = 'dark'
    elif args.light != False:
        theme = 'light'
    else:
        theme = 'auto'
    path = args.file

    while True:
        q = Queue()
        p = Process(target=main_task, args=(q, path, theme))
        p.start()
        p.join()

        if q.empty():
            break
        result = q.get()

        if isinstance(result, str):
            path = result
        else:
            break