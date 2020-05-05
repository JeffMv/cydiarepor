# cydiarepor
a python cydia repo parse tool to list and search deb to download

#### List cydia repo

```shell
$ python cydiarepor.py https://xia0z.github.io -l
-------------------------------------------------------------------
| N |           package            |             name             |
-------------------------------------------------------------------
|0  |       com.xia0.bloard        |            Bloard            |
|1  |      com.xia0.faketime       |           fakeTime           |
|2  |       com.xia0.fkiqyad       |           fkiqyad            |
|3  |     com.xia0.fkwatermark     |         fkwatermark          |
|4  |     com.xia0.fkwechatzan     |         fkwechatzan          |
|5  |     com.xia0.volume2home     |         volume2home          |
-------------------------------------------------------------------
```



#### Download deb by given search string

```shell
$ python cydiarepor.py https://xia0z.github.io -s "fk"
-------------------------------------------------------------------
| N |           package            |             name             |
-------------------------------------------------------------------
|0  |       com.xia0.fkiqyad       |           fkiqyad            |
|1  |     com.xia0.fkwatermark     |         fkwatermark          |
|2  |     com.xia0.fkwechatzan     |         fkwechatzan          |
-------------------------------------------------------------------
>> input number of deb want to download:0
[*] you choose 0 deb:"fkiqyad"
[*] start to download:fkiqyad
[+] download deb done
```


```shell
# Automation: make it download a preselected result.
# Passing --preselection 1 will download the middle package without
# waiting for user input.
$ python cydiarepor.py https://xia0z.github.io -s "fk" --preselection 1
-------------------------------------------------------------------
| N |           package            |             name             |
-------------------------------------------------------------------
|0  |       com.xia0.fkiqyad       |           fkiqyad            |
|1  |     com.xia0.fkwatermark     |         fkwatermark          |
|2  |     com.xia0.fkwechatzan     |         fkwechatzan          |
-------------------------------------------------------------------
[*] start to download:fkwatermark
[+] download deb done
```



#### Automation, Batch & Others

```shell
# Batch download by passing "all" instead of an index
$ python cydiarepor.py https://xia0z.github.io -s "fk" --preselection all
-------------------------------------------------------------------
| N |           package            |             name             |
-------------------------------------------------------------------
|0  |       com.xia0.fkiqyad       |           fkiqyad            |
|1  |     com.xia0.fkwatermark     |         fkwatermark          |
|2  |     com.xia0.fkwechatzan     |         fkwechatzan          |
-------------------------------------------------------------------
[*] ... # will download all the above packages
[+] download deb done   
```

**Example command explained**

```shell
# - Passing option -s will try to download packages containing "fk".
#     If you want to display all the packages, you can pass -s ''
#     since every package contains the empty string.
# - Option -d will use default sources to search for deb packages
# - The specified source (https://xia0z.github.io) will be parsed too
# - By passing "--preselection <an_index>", you will not be asked
#     for any input once the command is launched, and the package at
#     the selected index will be downloaded.
#     Thus, you could even integrate it in a script or other workflow.
#     Passing "all" to "--preselection" will download all the packages
#     matching the search term -s.
$ python cydiarepor.py https://xia0z.github.io -d -s "fk" --preselection all
```



#### List or search deb  by given search string in default cydia repo

here is the default cydia repo :

| Repo            | URL                                |
| --------------- | ---------------------------------- |
| BigBoss         | https://repounclutter.coolstar.org |
| Chimera Repo    | https://repo.chimera.sh            |
| Frida           | https://build.frida.re             |
| CoolStar's Repo | https://coolstar.org/publicrepo    |
| xia0Repo        | https://xia0z.github.io            |
| Bingner         | https://apt.bingner.com            |

try `python cydiarepor.py -d -l` or `python cydiarepor.py -d -s "Frida"`


#### Notes

- Use of HTTP instead of HTTPS: sometimes using a repo with httpS will result in an error, such as with repo httpS://apt.saurik.com/
    An error message would be printed if there was an error, and in that case you may prefer re-running your command using `http` instead.


#### Roadmap

**Done**

- [X] Listing deb files of several repositories
- [X] Searching for specific packages
- [X] Batch download of deb files

**To do**

- [ ] Source management (caching of repo packages and loading)
    - [X] Adding a new source
    - [X] Updating one source at a time
    - [ ] Updating all sources at once
    - [X] Saving downloaded package files
    - [X] Using the cached sources


#### Compatibility

The original work by [xia0@2019](https://4ch12dy.site) was using Python2.
See the original repo [here](https://github.com/4ch12dy/cydiarepor).

It has been update to use Python `3.6`. (It would be possible to make 
compatible with lower versions than `3.6` with a little more dev time though).


#### Enjoy it~
