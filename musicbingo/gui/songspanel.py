"""
Panels used for both available songs and songs in game
"""

from functools import partial
from typing import Callable, Dict, List, Set, Tuple, Union, cast

import tkinter as tk # pylint: disable=import-error
import tkinter.ttk # pylint: disable=import-error

from musicbingo.directory import Directory
from musicbingo.gui.panel import Panel
from musicbingo.options import GameMode, Options
from musicbingo.song import Duration, Song

#pylint: disable=too-many-instance-attributes
class SongsPanel(Panel):
    """
    Panel used for both available songs and songs in game
    """

    FOOTER_TEMPLATE = r"{num_songs} songs available ({duration})"
    COLUMNS = ("filename", "title", "artist", "album", "duration",)
    DISPLAY_COLUMNS = ('title', 'artist',)

    def __init__(self, main: tk.Frame, options: Options,
                 double_click: Callable[[List[Song]], None]) -> None:
        super(SongsPanel, self).__init__(main)
        self.inner = tk.Frame(self.frame)
        self.options = options
        self.on_double_click = double_click
        self._duration: int = 0
        self._num_songs: int = 0
        self._data: Dict[int, Union[Directory, Song]] = {}
        self._hidden: Set[int] = set()
        self._sorting: Tuple[str, bool] = ('', True)
        scrollbar = tk.Scrollbar(self.inner)
        self.tree = tkinter.ttk.Treeview(
            self.inner, columns=self.COLUMNS,
            displaycolumns=self.DISPLAY_COLUMNS,
            height=20,
            yscrollcommand=scrollbar.set)
        self.tree.column('#0', width=20, anchor='center')
        for column in self.DISPLAY_COLUMNS:
            self.tree.column(column, width=200, anchor='center')
            self.tree.heading(column, text=column.title(),
                              command=partial(self.sort, column, True))
        scrollbar.config(command=self.tree.yview)
        self.title = tk.Label(
            self.frame, text='',
            padx=5, bg=self.NORMAL_BACKGROUND, fg="#FFF",
            font=(self.TYPEFACE, 16))
        self.footer = tk.Label(
            self.frame, text='', padx=5, bg=self.NORMAL_BACKGROUND,
            fg="#FFF", font=(self.TYPEFACE, 14))
        self.tree.bind("<Double-1>", self.double_click)
        self.tree.pack(side=tk.LEFT)
        scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        self.title.pack(side=tk.TOP, pady=10)
        self.inner.pack(side=tk.TOP, pady=10)
        self.footer.pack(side=tk.BOTTOM)

    def disable(self):
        """disable panel"""
        self.tree.state(("disabled",))

    def enable(self):
        """enable panel"""
        self.tree.state(("!disabled",))

    def add_directory(self, directory: Directory) -> None:
        """Add directory contents to the TreeView widget"""
        self._add_directory(directory, '')
        self._update_footer()

    def _add_directory(self, directory: Directory, parent: str) -> None:
        """
        Internal API used for adding directory contents to the TreeView widget
        """
        for sub_dir in directory.subdirectories:
            item_id = self.tree.insert(
                parent, 'end', str(sub_dir.ref_id),
                values=(sub_dir.filename, sub_dir.title, '', '', '',),
                open=False)
            self._add_directory(sub_dir, item_id)
        self._data[directory.ref_id] = directory
        for song in directory.songs:
            self._data[song.ref_id] = song
            self.tree.insert(parent, 'end', str(song.ref_id),
                             values=song.pick(self.COLUMNS))
            self._duration += int(song.duration)
            self._num_songs += 1

    def add_song(self, song: Song) -> None:
        """Add a song to this panel"""
        self._data[song.ref_id] = song
        self.tree.insert('', 'end', str(song.ref_id),
                         values=song.pick(self.COLUMNS))
        self._duration += int(song.duration)
        self._num_songs += 1
        self._update_footer()

    def clear(self):
        """remove all songs from Treeview"""
        children = self.tree.get_children()
        if children:
            self.tree.delete(*children)
        self._duration = Duration(0)
        self._num_songs = 0
        self._data = {}

    def hide_song(self, song: Song, update: bool = True) -> None:
        """
        Hide one song from this panel.
        @raises KeyError if song not in this panel
        """
        _ = self._data[song.ref_id]
        self._hidden.add(song.ref_id)
        self.tree.detach(str(song.ref_id))
        self._duration -= int(song.duration)
        self._num_songs -= 1
        if update:
            self._update_footer()

    def restore_all(self) -> None:
        """Restores all hidden songs"""
        songs = [self._data[ref_id] for ref_id in self._hidden]
        for song in songs:
            self.restore_song(cast(Song, song))

    def restore_song(self, song: Song, update: bool = True) -> None:
        """
        Restores a hidden song from this panel.
        @raises KeyError if song not in this panel
        """
        self._hidden.remove(song.ref_id)
        if song._parent is not None:
            parent = str(cast(Directory, song._parent).ref_id)
            if int(parent) not in self._data:
                parent = ''
        else:
            parent = ''
        songs: List[Union[Song, Directory]] = []
        if self.tree.exists(parent):
            songs = [self._data[int(rid)] for rid in self.tree.get_children(parent)]
        songs.append(song)
        column, reverse = self._sorting
        songs.sort(key=lambda s: getattr(s, column), reverse=reverse)
        index: int = 0
        for item in songs:
            if item.ref_id == song.ref_id:
                break
            index += 1
        try:
            self.tree.reattach(str(song.ref_id), parent, index)
        except tk.TclError as err:
            print(err)
            print(song.ref_id, parent, index)
            self.tree.insert(parent, 'end', str(song.ref_id),
                             values=song.pick(self.COLUMNS))

        self._duration += int(song.duration)
        self._num_songs += 1
        if update:
            self._update_footer()

    def remove_song(self, song: Song, update: bool = True) -> None:
        """
        Remove one song from this panel.
        @raises KeyError if song not in this panel
        """
        del self._data[song.ref_id]
        self.tree.delete(str(song.ref_id))
        self._duration -= int(song.duration)
        self._num_songs -= 1
        if update:
            self._update_footer()

    def remove_directory(self, directory: Directory,
                         update: bool = True) -> None:
        """
        Remove all songs from one directory from this panel.
        @raises KeyError if directory not in this panel
        """
        del self._data[directory.ref_id]
        self.tree.delete(str(directory.ref_id))
        for sub_dir in directory.subdirectories:
            try:
                self.remove_directory(sub_dir, False)
            except KeyError as err:
                print(err)
        for song in directory.songs:
            try:
                self.remove_song(song, False)
            except KeyError:
                pass
        if update:
            self._update_footer()

    def set_title(self, title: str) -> None:
        """Set the title at the top of this panel"""
        self.title.config(text=title)

    def get_title(self) -> str:
        """Get the title at the top of this panel"""
        return self.title.cget('text')

    def _update_footer(self):
        """
        Update the duration text at the bottom of the treeview.
        This function is called after any addition or removal of songs
        to/from the lists.
        """
        txt = self.FOOTER_TEMPLATE.format(
            num_songs=self._num_songs,
            duration=Duration(self._duration).format())
        self.footer.config(text=txt)

    def sort(self, column: Union[str, Tuple[str]], reverse: bool = False) -> None:
        """
        Sort whole tree.
        The sort is recursive, so that each level is individually
        sorted. The sort can be multi-level by specifying a tuple
        of column names.
        """
        if not isinstance(column, str):
            for col in column:
                self.sort(col, reverse)
            return
        self._sorting = (column, reverse)
        self._sort_level('', column, reverse)
        # update heading to sort in other direction if clicked upon
        if column in self.DISPLAY_COLUMNS:
            self.tree.heading(
                column, command=partial(self.sort, column, not reverse))

    def _sort_level(self, parent: str, column: str, reverse: bool) -> None:
        """
        Sort specified directory level and then any children of that
        level.
        """
        # create tuple of the value of selected column + its ID for
        # each item at this level of the tree
        has_children = False
        pairs: List[Tuple[str, str]] = []
        for ref_id in self.tree.get_children(parent):
            value = Song.clean(self.tree.set(ref_id, column)).lower()
            pairs.append((value, ref_id,))
            children = self.tree.get_children(ref_id)
            if children:
                self._sort_level(ref_id, column, reverse)
                has_children = True

        if has_children and column != 'filename':
            return

        pairs.sort(reverse=reverse)

        # rearrange items into sorted positions
        for index, (_, ref_id) in enumerate(pairs):
            self.tree.move(ref_id, parent, index)

    def selections(self, focus: bool) -> List[Song]:
        """
        Return list of selected songs in this panel.
        If focus == true, only explictly selected items are returned
        If focus == false, all songs are returned if no items have
        been selected.
        """
        ref_ids = list(self.tree.selection())
        if not ref_ids:
            focus_elt = self.tree.focus()
            if focus and not focus_elt:
                return []
            if focus_elt:
                ref_ids = [focus_elt]
            else:
                ref_ids = self.tree.get_children()
        selections: List[Song] = []
        for rid in map(int, ref_ids):
            item = self._data[rid]
            if isinstance(item, Directory):
                selections += item.get_songs(rid)
            else:
                selections.append(item)
        return selections

    def all_songs(self) -> List[Song]:
        """get list of all songs in this panel"""
        songs: List[Song] = []
        for rid in map(int, self.tree.get_children()):
            item = self._data[rid]
            if isinstance(item, Directory):
                songs += cast(Directory, item).get_songs(rid)
            else:
                songs.append(item)
        return songs

    def get_song_ids(self) -> Set[int]:
        """get ref_id values for every song in panel"""
        return set(self._data.keys())

    #pylint: disable=unused-argument
    def double_click(self, event):
        """called when the treeview is double clicked"""
        selections = self.selections(True)
        if selections:
            self.on_double_click(selections)


class SelectedSongsPanel(SongsPanel):
    """
    Panel used for songs in game
    """
    FOOTER_TEMPLATE = r"Songs {mode} = {num_songs} ({duration})"

    def add_directory(self, directory: Directory) -> None:
        """Add directory contents to the TreeView widget"""
        super(SelectedSongsPanel, self).add_directory(directory)
        self.choose_title()

    def add_song(self, song: Song) -> None:
        """Add a song to this panel"""
        super(SelectedSongsPanel, self).add_song(song)
        self.choose_title()

    def remove_song(self, song: Song, update: bool = True) -> None:
        """
        Remove one song from this panel.
        @raises KeyError if song not in this panel
        """
        super(SelectedSongsPanel, self).remove_song(song, update)
        self.choose_title()

    def clear(self):
        """remove all songs from Treeview"""
        super(SelectedSongsPanel, self).clear()
        self.choose_title()

    def choose_title(self) -> None:
        """try to find a suitable title based upon the songs in the game"""
        folders: Set[str] = set()
        parents: Set[str] = set()
        for item in self._data.values():
            if not isinstance(item, Song):
                continue
            if item._parent is not None:
                folders.add(cast(Directory, item._parent).filename)
                if (item._parent._parent is not None and
                        item._parent._parent._parent is not None):
                    parents.add(cast(Directory, item._parent._parent).filename)
        if len(folders) == 1:
            self.set_title(folders.pop())
        elif len(parents) == 1:
            self.set_title(parents.pop())
        else:
            self.set_title('')

    def _update_footer(self):
        """
        Update the duration text at the bottom of the panel.
        This function is called after any addition or removal of songs
        to/from the lists.
        """
        if self._num_songs < 30:
            box_col = "#ff0000"
        elif self._num_songs < 45:
            box_col = "#fffa20"
        else:
            box_col = "#00c009"
        if self.options.mode == GameMode.CLIP:
            mode = "to clip"
        elif self.options.mode == GameMode.QUIZ:
            mode = "in quiz"
        else:
            mode = "in game"
        txt = self.FOOTER_TEMPLATE.format(
            mode=mode,
            num_songs=self._num_songs,
            duration=Duration(self._duration).format())
        self.footer.config(text=txt, fg=box_col)