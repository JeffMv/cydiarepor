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

```shell
# Passing option -s will download packages. Add Batch download all 
# packages containing "winterboard" in all the default sources + the
# one specified. By passing "--preselection all", you will not be asked
# for any input once the command is launched. Thus, you could even integrate
# it in a whole workflow
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
    - [ ] Searching from the cached sources


#### Compatibility

The original work by [xia0@2019](https://4ch12dy.site) was using Python2.
See the original repo [here](https://github.com/4ch12dy/cydiarepor).

It has been update to use Python `3.6`. (It would be possible to make 
compatible with lower versions than `3.6` with a little more dev time though).


#### Enjoy it~
