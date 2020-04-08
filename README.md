# rMsync

Synchronization script for the reMarkable e-reader. The idea is to have a "Library" folder on your PC which is synchronized with the reMarkable. When new files appear in this local directory this script will push them over to the rM. When files are edited, created or annotated on the rM they get converted to .pdf (from .rm) and copied back to the Library folder (with the suffix "_annot"). Notes are also converted to PDF and saved to a Notes directory (and not reuploaded).

The file structure might look like this:
```
|--Literature
    |--Papers
    |--Books
    |--Notes
```
Adjust the paths at the top of the script!

### Requirements
* imagemagick
* pdftk
* https://github.com/lschwetlick/maxio/tree/master/rm_tools
* ( https://github.com/reHackable/scripts )

### Usage
```
usage: sync.py [-b] [-c] [-u] [-d] [-l]

optional arguments:
  -b, --backup                        download files from the connected rM
  -c, --convert                       convert the backed up lines files to annotated pdfs and notes
  -u, --upload                        upload new files from the library directory to the rM
  -d, --dry_upload                    runs upload function but without actually pushing anything (just for debugging)
  -p --purge                          delete old backup before making new backup
```

### Example
```
python3 sync.py -bcu #backup, convert and upload: full sync
```

### Notes
8.4.2020 updated to work with rM version 2.0.2