import tkinter as tk
from PIL import Image, ImageTk
from tkinter import filedialog as fd, Label
from skimage.metrics import structural_similarity as ssim
import numpy as np
import cv2
import os

class MousePositionTracker(tk.Frame):
    """ Tkinter Canvas mouse position widget. """

    def __init__(self, canvas):
        self.end = (0, 0)
        self.start = (0, 0)
        self.canvas = canvas
        self.canv_width = self.canvas.cget('width')
        self.canv_height = self.canvas.cget('height')
        #self.reset()

        # Create canvas cross-hair lines.
        xhair_opts = dict(dash=(3, 2), fill='white', state=tk.HIDDEN)
        self.lines = (self.canvas.create_line(0, 0, 0, self.canv_height, **xhair_opts),
                      self.canvas.create_line(0, 0, self.canv_width,  0, **xhair_opts))

    def cur_selection(self):
        return (self.start, self.end)

    def begin(self, event):
        self.hide()
        self.start = (event.x, event.y)  # Remember position (no drawing).

    def update(self, event):
        self.end = (event.x, event.y)
        self._update(event)
        self._command(self.start, (event.x, event.y))  # User callback.

    def _update(self, event):
        # Update cross-hair lines.
        self.canvas.coords(self.lines[0], event.x, 0, event.x, self.canv_height)
        self.canvas.coords(self.lines[1], 0, event.y, self.canv_width, event.y)
        self.show()

    def reset(self):
        print("reset")
        self.start = self.end = None

    def hide(self):
        self.canvas.itemconfigure(self.lines[0], state=tk.HIDDEN)
        self.canvas.itemconfigure(self.lines[1], state=tk.HIDDEN)

    def show(self):
        self.canvas.itemconfigure(self.lines[0], state=tk.NORMAL)
        self.canvas.itemconfigure(self.lines[1], state=tk.NORMAL)

    def autodraw(self, command=lambda *args: None):
        """Setup automatic drawing; supports command option"""
        self.reset()
        self._command = command
        self.canvas.bind("<Button-1>", self.begin)
        self.canvas.bind("<B1-Motion>", self.update)
        self.canvas.bind("<ButtonRelease-1>", self.quit)

    def quit(self, event):
        self.hide()  # Hide cross-hairs.
        #self.reset()


class SelectionObject:
    """ Widget to display a rectangular area on given canvas defined by two points
        representing its diagonal.
    """
    def __init__(self, canvas, select_opts):
        # Create attributes needed to display selection.
        self.canvas = canvas
        self.select_opts1 = select_opts
        self.width = self.canvas.cget('width')
        self.height = self.canvas.cget('height')

        # Options for areas outside rectanglar selection.
        select_opts1 = self.select_opts1.copy()  # Avoid modifying passed argument.
        select_opts1.update(state=tk.HIDDEN)  # Hide initially.
        # Separate options for area inside rectanglar selection.
        select_opts2 = dict(dash=(2, 2), fill='', outline='white', state=tk.HIDDEN)

        # Initial extrema of inner and outer rectangles.
        imin_x, imin_y,  imax_x, imax_y = 0, 0,  1, 1
        omin_x, omin_y,  omax_x, omax_y = 0, 0,  self.width, self.height

        self.rects = (
            # Area *outside* selection (inner) rectangle.
            self.canvas.create_rectangle(omin_x, omin_y,  omax_x, imin_y, **select_opts1),
            self.canvas.create_rectangle(omin_x, imin_y,  imin_x, imax_y, **select_opts1),
            self.canvas.create_rectangle(imax_x, imin_y,  omax_x, imax_y, **select_opts1),
            self.canvas.create_rectangle(omin_x, imax_y,  omax_x, omax_y, **select_opts1),
            # Inner rectangle.
            self.canvas.create_rectangle(imin_x, imin_y,  imax_x, imax_y, **select_opts2)
        )

    def update(self, start, end):
        # Current extrema of inner and outer rectangles.
        imin_x, imin_y,  imax_x, imax_y = self._get_coords(start, end)
        omin_x, omin_y,  omax_x, omax_y = 0, 0,  self.width, self.height

        # Update coords of all rectangles based on these extrema.
        self.canvas.coords(self.rects[0], omin_x, omin_y,  omax_x, imin_y),
        self.canvas.coords(self.rects[1], omin_x, imin_y,  imin_x, imax_y),
        self.canvas.coords(self.rects[2], imax_x, imin_y,  omax_x, imax_y),
        self.canvas.coords(self.rects[3], omin_x, imax_y,  omax_x, omax_y),
        self.canvas.coords(self.rects[4], imin_x, imin_y,  imax_x, imax_y),

        for rect in self.rects:  # Make sure all are now visible.
            self.canvas.itemconfigure(rect, state=tk.NORMAL)

    def _get_coords(self, start, end):
        """ Determine coords of a polygon defined by the start and
            end points one of the diagonals of a rectangular area.
        """
        return (min((start[0], end[0])), min((start[1], end[1])),
                max((start[0], end[0])), max((start[1], end[1])))

    def hide(self):
        for rect in self.rects:
            self.canvas.itemconfigure(rect, state=tk.HIDDEN)


class Application(tk.Frame):

    # Default selection object options.
    SELECT_OPTS = dict(dash=(2, 2), stipple='gray25', fill='red',
                          outline='')

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.canvas = None #used to make sure canvas is initialized before potentially forgoten
        self.displayNewCanvas()


    def displayNewCanvas(self):
        if self.canvas is not None:
            self.canvas.pack_forget()
        img = ImageTk.PhotoImage(Image.open(path))
        self.canvas = tk.Canvas(root, width=img.width(), height=img.height(), borderwidth=0, highlightthickness=0)
        self.canvas.pack(expand=True)

        self.canvas.create_image(0, 0, image=img, anchor=tk.NW)
        self.canvas.img = img  # Keep reference.

        # Create selection object to show current selection boundaries.
        self.selection_obj = SelectionObject(self.canvas, self.SELECT_OPTS)

        # Callback function to update it given two points of its diagonal.
        def on_drag(start, end, **kwarg):  # Must accept these arguments.
            self.selection_obj.update(start, end)

        # Create mouse position tracker that uses the function.
        self.posn_tracker = MousePositionTracker(self.canvas)

        self.posn_tracker.autodraw(command=on_drag)  # Enable callbacks.


def select_file():
    filetypes = (
        ('PNG file', '*.png'),
        ('JPEG file', '*.jpeg')

    )
    return fd.askopenfilename(
        title='Open a file',
        initialdir='/',
        filetypes=filetypes)


def select_file_update():
    global path
    path = select_file()
    app.displayNewCanvas()


def select_directory():
    global searchPath
    searchPath = fd.askdirectory(
        title='Open a directory',
        initialdir='/')
    path_label.configure(text="Search Path: "+searchPath)


def mse(imageA, imageB):
    # the 'Mean Squared Error' between the two images is the
    # sum of the squared difference between the two images;
    # NOTE: the two images must have the same dimension
    err = np.sum((imageA.astype("float") - imageB.astype("float")) ** 2)
    err /= float(imageA.shape[0] * imageA.shape[1])

    # return the MSE, the lower the error, the more "similar"
    # the two images are
    return err


def compare_images(imageA, imageB):
    # compute the mean squared error and structural similarity
    # index for the images
    m = mse(imageA, imageB)
    s = ssim(imageA, imageB, channel_axis=2)
    print("Mean Squared Error: ", m, "Strucutal Similarity Index: ", s)


def compare_selection_directory():
    #get image of mini-selection
    imagecv = cv2.imread(path)
    global app
    global good_matches
    good_matches = list()
    dim = app.posn_tracker.cur_selection()
    print("Selection dimensions: ", dim)
    mini_image = imagecv[dim[0][1]:dim[1][1], dim[0][0]:dim[1][0]]
    #test to make sure image shows
    #cv2.imshow("Image", mini_image)
    miniWidth, miniHeight, channels = mini_image.shape
    for root, dirs, files in os.walk(searchPath):
        for file in files:
            if file.endswith(".jpeg") or file.endswith(".png"):
                full_image = cv2.imread(os.path.join(root, file))
                if full_image is None:
                    break
                fullWidth, fullHeight, channels = full_image.shape
                xLoc = 0
                yLoc = 0
                found = False
                while xLoc<fullWidth-miniWidth-1 and not found:
                    yLoc = 0
                    while yLoc<fullHeight-miniHeight-1 and not found:
                        full_splice = full_image[xLoc:xLoc+miniWidth, yLoc:yLoc+miniHeight] #diminesions may be incorrect
                        print("xLoc: ", xLoc, "yLoc: ", yLoc, "miniWidth: ", miniWidth, "miniHeight: ", miniHeight, "file", os.path.join(root, file))
                        ssi_score = 0
                        if full_splice.shape==mini_image.shape:
                            ssi_score = ssim(mini_image, full_splice, channel_axis=2)

                        print(ssi_score)
                        if (ssi_score>0.80):
                            cv2.imshow(os.path.join(root, file), full_image)
                            cv2.waitKey(0)
                            cv2.destroyAllWindows()
                            good_matches.append(os.path.join(root, file))
                            found = True
                        yLoc += 1
                    xLoc += 1


if __name__ == '__main__':
    WIDTH, HEIGHT = 1920, 1080
    BACKGROUND = 'grey'
    TITLE = 'Image Cropper'
    root = tk.Tk()
    root.title(TITLE)
    root.geometry('%sx%s' % (WIDTH, HEIGHT))
    root.configure(background=BACKGROUND)

    # Create a file chooser
    path = select_file()

    app = Application(root, background=BACKGROUND)
    app.pack(side=tk.TOP, fill=tk.BOTH, expand=tk.TRUE)

    newfile_button = tk.Button(
        root,
        text='Open a New File',
        command=select_file_update
    )
    newfile_button.place(x= 50, y=HEIGHT-100)

    chooseSearch_button = tk.Button(
        root,
        text="Choose File Directory",
        command=select_directory
    )
    chooseSearch_button.place(x=WIDTH-300, y=HEIGHT-100)

    search_button = tk.Button(
        root,
        text='Search',
        command=compare_selection_directory
    )
    search_button.place(x=WIDTH-100, y=HEIGHT-100)
    searchPath = "Search Path:"

    path_label = Label(text=searchPath)
    path_label.place(x=WIDTH - 600, y=HEIGHT - 100)
    imageA = cv2.imread("apple.png")
    imageB = cv2.imread("appleMecury.png")
    print(imageA.shape, imageB.shape)
    compare_images(imageA, imageB)
    app.mainloop()
