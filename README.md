# rMsync

Synchronization script for the reMarkable e-reader. The idea is to have a "Library" folder on your PC which is synchronized with the reMarkable. When new files appear in this local directory this script will push them over to the rM. When files are edited, created or annotated on the rM they get converted to .pdf (from .lines) and copied back to the Library folder (with the suffix "_annot").

### Requirements
* imagemagick
* pdftk
* https://github.com/lschwetlick/maxio/tree/master/tools
* ( https://github.com/reHackable/scripts )

Adjust the paths at the top of the script to your setup before running!
Also, copy and paste `empty.rm` from [here](https://github.com/lschwetlick/maxio/tree/master/tools/convert_procedure).

### Usage
```
usage: sync.py [-b] [-c] [-u] [-d] [-l]

optional arguments:
  -b, --backup                        download files from the connected rM
  -c, --convert                       convert the backed up lines files to annotated pdfs and notes
  -u, --upload                        upload new files from the library directory to the rM
  -d, --dry_upload                    runs upload function but without actually pushing anything (just for debugging)
  -l, --makeList                      lists files in the backup directory in plain text (as opposed to hashed)
```

### Example

```
python3 sync.py -bcu #backup, convert and upload: full sync
```
