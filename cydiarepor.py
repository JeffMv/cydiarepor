#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
#import wget
import os
import sys
import argparse
import gzip
import io
import bz2
import urllib.parse
import json
import datetime
import math

__version__ = "0.2.6.0"


DEBUG_FLAG = 0
SOURCES_DIRECTORY = "sources"

def try_int(value):
    try:
        return int(value)
    except ValueError:
        return None


def try_decode_using_encodings(content, encodings):
    decoded = False
    remaining = encodings.copy()
    result = None
    encoding = None
    while not decoded and len(remaining) > 0:
        try:
            encoding = remaining.pop(0)
            result = content.decode(encoding=encoding)
            decoded = True
        except UnicodeDecodeError:
            pass
    return result, encoding


def join_url_path_components(base, path):
    """
    >>> expected = http://appsec-labs.com/cydia/Packages.bz2
    >>> join_url_path_components("http://appsec-labs.com/cydia/", "/Packages.bz2") == expected
    True
    >>> join_url_path_components("http://appsec-labs.com/cydia/", "Packages.bz2") == expected
    True
    >>> join_url_path_components("http://appsec-labs.com/cydia", "Packages.bz2") == expected
    True
    >>> join_url_path_components("http://appsec-labs.com/cydia", "/Packages.bz2") == expected
    True
    """
    lhas = base.endswith("/")
    rhas = path[0] == "/"
    if lhas and rhas:
        return base + path[1:]
    elif lhas or rhas:
        return base + path
    else:
        return base + "/" + path


def get_default_cydia_repo_array():
    default_repos = []
    # BigBoss of coolstar
    default_repos.append("https://repounclutter.coolstar.org")
    default_repos.append("https://repo.chimera.sh")
    default_repos.append("https://build.frida.re")
    default_repos.append("https://coolstar.org/publicrepo")
    default_repos.append("https://apt.bingner.com")
    default_repos.append("https://xia0z.github.io")
    
    return default_repos

def get_repo_slugname(repo):
    """
    >>> get_repo_slugname("https://build.frida.re")
    build.frida.re
    >>> get_repo_slugname("https://build.frida.re/./foo/bar")
    build.frida.re
    >>> get_repo_slugname("://build.frida.re")
    build.frida.re
    """
    parse_result = urllib.parse.urlparse(repo)
    return parse_result.netloc

    
def handle_old_cydia_repo(url):
    parse_result = urllib.parse.urlparse(url)
    scheme = '{uri.scheme}'.format(uri=parse_result)
    url = url[len(scheme):]
    scheme = "http://" if not scheme else scheme
    
    old_BigBoss_repo = "://apt.thebigboss.org/repofiles/cydia"
    old_bingner_repo = "://apt.bingner.com"
    old_Saurik_repo = "://apt.saurik.com"
    repo_package_url = ""
    zip_type = ""
    ret = []
    
    if url.find(old_BigBoss_repo) >= 0:
        repo_package_url = scheme+old_BigBoss_repo + "/dists/stable/main/binary-iphoneos-arm/Packages.bz2"
        zip_type = "bz2"
        ret.append(repo_package_url)
        ret.append(zip_type)
    elif url.find(old_bingner_repo) >= 0:
        repo_package_url = scheme+old_bingner_repo + "/dists/ios/1443.00/"+"main/binary-iphoneos-arm/Packages.bz2"
        zip_type = "bz2"
        ret.append(repo_package_url)
        ret.append(zip_type)
    elif url.find(old_Saurik_repo) >= 0:
        # http://apt.saurik.com/dists/ios/1452.23/main/binary-iphoneos-arm/Packages.bz2
        repo_package_url = scheme+old_Saurik_repo + "/dists/ios/1452.23/"+"main/binary-iphoneos-arm/Packages.bz2"
        zip_type = "bz2"
        ret.append(repo_package_url)
        ret.append(zip_type)
        pass
    else:
        ret = None
    
    return ret


def similar_url_radicals(url1, url2, compare_trailing=False):
    """
    """
    radical_path = lambda url: url[:-1] if url.endswith("/") else url
    
    parsed_url1 = urllib.parse.urlparse(url1)
    parsed_url2 = urllib.parse.urlparse(url2)
    ## >>> urllib.parse.urlparse("http://appsec-labs.com/cydia/#yosam?fizz=bar&foo=tchi")
    ## ... ParseResult(scheme='http', netloc='appsec-labs.com', path='/cydia/', params='', query='', fragment='yosam?fizz=bar&foo=tchi')
    # scheme = '{uri.scheme}'.format(uri=parse_result)
    if parsed_url1.netloc != parsed_url2.netloc:
        return False
    if radical_path(parsed_url1.path) != radical_path(parsed_url2.path):
        return False
    
    if compare_trailing:
        same_fragment = parsed_url1.fragment == parsed_url2.fragment
        same_query = parsed_url1.query == parsed_url2.query
        if not same_fragment or not same_query:
            return False
    
    return True


def is_url_reachable(url):
    # not allowing redirects would prevent auto switching from http to https
    # r = requests.get(url, allow_redirects = False)
    #
    try:
        r = requests.get(url, allow_redirects = True)
    except requests.adapters.SSLError:
        print(f"SSLError with repo {url}. Please use HTTP instead of HTTPS if there is any issue")
        assert url.count("https://") <= 1, "URL is probably mistyped"
        secure_less_url = url.replace("https://", "http://")
        r = requests.get(secure_less_url, allow_redirects = True)
    status = r.status_code
    
    if not similar_url_radicals(r.url, url):
        return False
    
    if status == 200:
        return True
    
    return False


def try_uncompress(data):
    zip_type =  None
    decoded = data
    did_uncompress = False
    
    res1, zip_type1 = unzip_data_to_string(data, 'gz'), 'gz'
    res2, zip_type2 = unzip_data_to_string(data, 'bz2'), 'bz2'
    
    if res1 or res2:
        decoded = res1 if res1 is not None else res2
        zip_type = zip_type1 if zip_type1 is not None else zip_type2
        did_uncompress = True
    
    return did_uncompress, decoded, zip_type


def unzip_data_to_string(data, unzip_type):
    unzip_string = ""
    try:
        if unzip_type == "gz":
            if isinstance(data, bytes):
                compressedstream = io.BytesIO(data)
            else:
                compressedstream = io.StringIO(data)
            
            gziper = gzip.GzipFile(fileobj=compressedstream)
            unzip_string = gziper.read()
        elif unzip_type == "bz2":
            unzip_string = bz2.decompress(data)
        else:
            return None
    except OSError:
        return None
    except Exception as err:
        print(f"Error while unarchiving: {err}")
        raise err
    
    return unzip_string
    
def http_get(url):
    r = requests.get(url, stream=True)
    return r

def parse_raw_deb_info_string(package_string):
    '''
    A package string looks like this:
Package: com.ex.substitute
Version: 0.0.13
Architecture: iphoneos-arm
Maintainer: Sam Bingner
Installed-Size: 640
Pre-Depends: coreutils-bin, dpkg (>=1.17.11)
Depends: firmware (>= 8.0), cy+cpu.arm64, com.saurik.substrate.safemode, mobilesubstrate (=0.9.7033+dummy), uikittools (>=1.1.13-4), darwintools
Conflicts: com.ex.libsubstitute, org.coolstar.tweakinject, science.xnu.substitute
Replaces: com.ex.libsubstitute, org.coolstar.tweakinject
Provides: com.ex.libsubstitute, mobilesubstrate
Filename: debs/1443.00/com.ex.substitute_0.0.13_iphoneos-arm.deb
Size: 41700
MD5sum: bde1c679eda881d2dad2d314ade7c181
SHA1: 506a96ef1c72ed67544919400676f325d5d1b428
SHA256: 1e093c144e33bce9afa4eb5d20b6e72b1e5ffeb63f1e79815a3609c982ffe65a
Section: System
Priority: optional
Description: Substrate substitute for code substitution
Author: comex <comexk+da@gmail.com>
Name: Substitute
    '''
    entries = package_string.split("\n")
    keys = list(map(lambda x:x.split(":")[0], entries))
    values = list(map(lambda x:":".join(x.split(":")[1:])[1:], entries))
    
    kv = {key:values[i] for i, key in enumerate(keys)}
    orig = kv.copy()
    # 
    kv_list_entries = {key:[value_i.strip() for value_i in kv[key].split(",")] for key in kv if kv[key].count(",") > 0}
    kv.update(kv_list_entries)
    
    # These keys must not be turned to arrays (comma not to interpret as different values of array)
    keys_to_preserve_as_is = ["Description", "Package", "Version", "Filename", "Name"]
    for a_key in keys_to_preserve_as_is:
        kv[a_key] = orig.get(a_key, "")
    
    return kv


def merge_on_empty_fields(base, tomerge):
    """Utility to quickly fill empty or falsy field of $base with fields
    of $tomerge 
    """
    has_merged_anything = False
    for key in tomerge:
        if not base.get(key):
            base[key] = tomerge.get(key)
            has_merged_anything = True
    return has_merged_anything

def is_malformed_deb_infos(deb):
    valid_fields = [key for key in deb if len(key) > 0 and len(deb[key]) > 0]
    return len(valid_fields) == 0


def get_cydiarepo_reachable_url(repoURL):
    # cydiarepo_Packages_URL = repoURL + '/Packages'
    # cydiarepo_Packages_bz2_URL = repoURL + '/Packages.bz2'
    # cydiarepo_Packages_gz_URL = repoURL + '/Packages.gz'
    # print(f"cydiarepo_Packages_URL: {cydiarepo_Packages_URL}")
    cydiarepo_Packages_URL = join_url_path_components(repoURL, '/Packages')
    cydiarepo_Packages_bz2_URL = join_url_path_components(repoURL, '/Packages.bz2')
    cydiarepo_Packages_gz_URL = join_url_path_components(repoURL, '/Packages.gz')
    # print(f"cydiarepo_Packages_URL: {cydiarepo_Packages_URL}")
    
    cydiarepo_reachable_URL = None
    usesDebian = None
    
    if handle_old_cydia_repo(repoURL):
        ret = handle_old_cydia_repo(repoURL)
        zip_type = ret[1]
        if zip_type == "gz":
            cydiarepo_Packages_gz_URL = ret[0]
            usesDebian = True
        elif zip_type == "bz2":
            cydiarepo_Packages_bz2_URL = ret[0]
            usesDebian = True
        else:
            # print("[-] unknown old cydia repo zip type")
            # exit(1)
            return cydiarepo_reachable_URL, usesDebian
    
    is_need_unzip = False
    unzip_type = ''
    
    usesDebian = usesDebian if usesDebian is True else False
    if is_url_reachable(cydiarepo_Packages_URL):
        cydiarepo_reachable_URL = cydiarepo_Packages_URL
    elif is_url_reachable(cydiarepo_Packages_bz2_URL):
        cydiarepo_reachable_URL = cydiarepo_Packages_bz2_URL
        is_need_unzip = True
        unzip_type = "bz2"
        
    elif is_url_reachable(cydiarepo_Packages_gz_URL):
        cydiarepo_reachable_URL = cydiarepo_Packages_gz_URL
        is_need_unzip = True
        unzip_type = "gz"
    else:
        # print(("[-] {} : did not find Packages or Packages.bz2 or Packages.gz file in this repo, verify it!".format(repoURL)))
        # exit(1)
        return cydiarepo_reachable_URL, None
        pass
    return cydiarepo_reachable_URL, usesDebian


def get_packages_file_from_cydiarepoURL(repoURL):
    # cydiarepo_Packages_URL = repoURL + '/Packages'
    # cydiarepo_Packages_bz2_URL = repoURL + '/Packages.bz2'
    # cydiarepo_Packages_gz_URL = repoURL + '/Packages.gz'
    # print(f"cydiarepo_Packages_URL: {cydiarepo_Packages_URL}")
    cydiarepo_Packages_URL = join_url_path_components(repoURL, '/Packages')
    cydiarepo_Packages_bz2_URL = join_url_path_components(repoURL, '/Packages.bz2')
    cydiarepo_Packages_gz_URL = join_url_path_components(repoURL, '/Packages.gz')
    # print(f"cydiarepo_Packages_URL: {cydiarepo_Packages_URL}")
    
    if handle_old_cydia_repo(repoURL):
        ret = handle_old_cydia_repo(repoURL)
        zip_type = ret[1]
        if zip_type == "gz":
            cydiarepo_Packages_gz_URL = ret[0]
        elif zip_type == "bz2":
            cydiarepo_Packages_bz2_URL = ret[0]
        else:
            print("[-] unknown old cydia repo zip type")
            exit(1)
    
    cydiarepo_reachable_URL = ''
    is_need_unzip = False
    unzip_type = ''
    
    if is_url_reachable(cydiarepo_Packages_URL):
        cydiarepo_reachable_URL = cydiarepo_Packages_URL
    elif is_url_reachable(cydiarepo_Packages_bz2_URL):
        cydiarepo_reachable_URL = cydiarepo_Packages_bz2_URL
        is_need_unzip = True
        unzip_type = "bz2"
        
    elif is_url_reachable(cydiarepo_Packages_gz_URL):
        cydiarepo_reachable_URL = cydiarepo_Packages_gz_URL
        is_need_unzip = True
        unzip_type = "gz"
    else:
        print(("[-] {} : did not find Packages or Packages.bz2 or Packages.gz file in this repo, verify it!".format(repoURL)))
        exit(1)

    try:
        resp = requests.get(cydiarepo_reachable_URL)
    except requests.adapters.SSLError:
        # server issue with httpS -> use http
        print(f"SSLError with repo {cydiarepo_reachable_URL}. Please use HTTP instead of HTTPS if there is any issue")
        assert url.count("https://") <= 1, "URL is probably mistyped"
        cydiarepo_reachable_URL = url.replace("https://", "http://")
        resp = requests.get(cydiarepo_reachable_URL)
    
    raw_packages_data = resp.content
    return raw_packages_data, is_need_unzip, unzip_type, cydiarepo_reachable_URL, resp.encoding


def get_raw_unarchived_packages_file_from_cydiarepoURL(repoURL):
    tmp = get_packages_file_from_cydiarepoURL(repoURL)
    raw_packages_data, is_need_unzip, unzip_type, cydiarepo_reachable_URL = tmp[:4]
    encoding = tmp[4]
    
    did_uncompress, decoded, zip_type = try_uncompress(raw_packages_data)
    if did_uncompress:
        raw_packages_unarchived = decoded
    else:
        raw_packages_unarchived = raw_packages_data
    
    return raw_packages_unarchived, cydiarepo_reachable_URL, encoding


def get_raw_packages_list_from_cydiarepoURL(repoURL):
    raw_packages_unarchived, _, encoding = get_raw_unarchived_packages_file_from_cydiarepoURL(repoURL)
    
    if encoding:
        raw_packages_string = raw_packages_unarchived.decode(encoding=encoding)
    else:
        raw_packages_string = raw_packages_unarchived.decode()
    
    raw_packages_list = raw_packages_string.split("\n\n")
    return raw_packages_list

def extract_raw_packages_list_from_content(content):
    raw_packages_list = content.split("\n\n")
    return raw_packages_list


def get_debs_from_cydiarepo(repoURL, from_remote=False):
#    Package: com.archry.joker
#    Version: 1.0.30-1+debug
#    Architecture: iphoneos-arm
#    Installed-Size: 588
#    Depends: mobilesubstrate
#    Filename: ./debs/com.archry.joker.deb.deb
#    Size: 117922
#    MD5sum: c5d30e1b10177190ee56eecf5dbb5cfe
#    SHA1: 377d5c59926083b2acdd95028abe24edfeba6141
#    SHA256: fcb97af34c56d4a2bd67540df0427cb0cbd9b68e4c4e78f555265c3db1e2b67e
#    Section: Hack
#    Description: Archery king hack winde , zoom  and better Aiming
#    Author: @Kgfunn
#    Depiction: https://joker2gun.github.io/depictions/?p=com.archry.joker
#    Name: Archery King Hack
    filepath = filepath_for_repo_source(repoURL)
    if os.path.exists(filepath) and not from_remote:
        with open(filepath) as fh:
            raw_packages_list = extract_raw_packages_list_from_content(fh.read())
    else:
        raw_packages_list = get_raw_packages_list_from_cydiarepoURL(repoURL)
    
    repo_info = {"url":repoURL}
    k_need_item_array = ["Package", "Version", "Filename", "Name", "Description"]
    all_deb = []
    for raw_package_string in raw_packages_list:
        raw_deb_list = raw_package_string.split("\n")
        cur_deb = {}
        
        ## This helper parser `parse_raw_deb_info_string` was added after the
        ## original codebase in order not to mess up previous things, the
        ## original codebase is used, and this will be added on top to patch
        ## things that often have caused issues during further testing
        reference_info_deb = parse_raw_deb_info_string(raw_package_string)
        
        if DEBUG_FLAG >= 2:
            print(f"{'='*60}\n>> raw_package_string\n{raw_package_string}")
            print(f"{'-'*60}\nparsed package string\n{json.dumps(reference_info_deb, indent=2)}")
        
        for raw_deb_str in raw_deb_list:
            deb_item = raw_deb_str.split(":")

            if len(deb_item) != 2:
                continue
            deb_item_k = deb_item[0].strip()
            deb_item_v = deb_item[1].strip()
            
            need_item_array = k_need_item_array
            if deb_item_k in need_item_array:
                cur_deb[deb_item_k] = deb_item_v
            
            for k in need_item_array:
                if k not in cur_deb:
                    cur_deb[k] = ""
            
            cur_deb["repo"]=repo_info
        
        
        ## using new codebase's utility's parsing result since the original
        ## codebase produced inconsistencies and errors
        cur_deb["Filename"] = cur_deb.get("Filename", reference_info_deb.get("Filename", ""))
        # actually not required at time of writing, but provides extra
        # information and may help prevent parsing errors made by the original
        # codebase
        did_merge = merge_on_empty_fields(cur_deb, reference_info_deb)
        
        if cur_deb and not is_malformed_deb_infos(cur_deb):
            all_deb.append(cur_deb)
    
    return all_deb
    

def get_debs_in_cydia_repos(repo_urls):
    debs_infos = []
    
    for url in repo_urls:
        debs = get_debs_from_cydiarepo(url, False)
        debs_infos += debs
        
    return debs_infos


def is_need_by_search_string(deb, contained_str):
    name = deb['Name']
    package = deb['Package']
    description = ''
    if 'Description' in deb:
        description = deb['Description']
    
    if contained_str in description:
        return True
    
    if contained_str in name or contained_str in package:
        return True
    
    return False


def url_deb_file(repo_url, deb):
    deb_download_url = repo_url + "/./" + deb['Filename']
    return deb_download_url

def is_empty_deb_file_url(repo_url, deb):
    # example empty url:  https://apt.bingner.com/./
    # instead of a real deb file url like:
    # https://apt.bingner.com/./debs/1443.00/coreutils_8.31-1_iphoneos-arm.deb
    url = url_deb_file(repo_url, deb)
    return (url == repo_url + "/./") or url.split('?')[0].endswith('/')


def savepath_for_deb(repo_url, deb, slug_subdir):
    """
    :param bool slug_subdir: whether it should create subfolders in downloads
                    directory or not. Subfolders would be named after the repo
    """
    fname = deb['Package'] + "_"+ deb['Version'] + ".deb"    
    # dest = "."
    dest = "downloads"
    dest = os.path.join(dest, (get_repo_slugname(repo_url) if slug_subdir else ''))
    savepath = os.path.join(dest, fname)
    return savepath


def download_deb_file(repo_url, deb, overwrite=False, slug_subdir=True):
    """
    :param str repo_url:
    :param bool overwrite:
    :param bool slug_subdir: whether it should create subfolders in downloads
                    directory or not. Subfolders would be named after the repo
    :return: whether the resource was fetched
    """
    deb_download_url = repo_url + "/./" + deb['Filename']
    print(f"    {deb_download_url}")
    fname = deb['Package'] + "_"+ deb['Version'] + ".deb"    
    filepath = savepath_for_deb(repo_url, deb, slug_subdir)
    
    if overwrite or not os.path.exists(filepath):
        r = http_get(deb_download_url)
        deb_data = r.content
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'wb') as f:
            f.write(deb_data)
#       wget.download(deb_download_url, filepath)
        return False
    else:
        return True

def list_all_repo_deb(debs):
    print(("-"*(3+30+30+4)))
    title = "Developed By xia0@2019 Blog: https://4ch12dy.site"
    print(("|"+format(title,"^65")+"|"))
    title = "  Improved by JeffMv : https://github.com/JeffMv"
    print(("|"+format(title,"^65")+"|"))
    
    print(("-"*(3+30+30+4)))
    total_str = "Total:{}".format(len(debs))
    print(("|"+format(total_str,"^65")+"|"))
    print(("-"*(3+30+30+4)))
    print(("|"+format("N", "^3") + "|" + format("package", "^30")+"|"+format("name", "^30")+"|"))
    print(("-"*(3+30+30+4)))
    for i in range(len(debs)):
        if (i+1) % 40 == 0:
            print(("|"+format(i,"<3")+"|" + format(debs[i]["Package"], "^30")+ "|" + format(debs[i]["Name"]+"("+debs[i]["Version"]+")", "^30") + "|"))
            print(("-"*(3+30+30+4)))
            choice = input("|" + "do you want to continue? [Y/N]: ")
            print(("-"*(3+30+30+4)))
            if choice.lower() in ['n', 'N', '0']:
                break
            elif choice.lower() in ['y', 'Y', '1']:
                continue
            else:
                print("[-] error choice")
                exit(1)
    
        print(("|"+format(i,"<3")+"|" + format(debs[i]["Package"], "^30")+ "|" + format(debs[i]["Name"], "^30") + "|"))
    
    print(("-"*(3+30+30+4)))
    
def list_deb(debs):
    _problematic_debs = []
    
    com_item_wid = 30
    total_wid = 1+3+ (com_item_wid +1) *3 + 1
    
    print(("-"*total_wid))
    print(("|"+format("N", "^3") + "|" + format("package", "^30")+"|"+format("name", "^30")+"|"+format("repo url", "^30")+"|"))
    print(("-"*total_wid))
    for i in range(len(debs)):
        try:
            print(("|"+format(i,"<3")+"|" + format(debs[i]["Package"], "^30")+ "|" + format(debs[i]["Name"]+"("+debs[i]["Version"]+")", "^30") + "|" + format(debs[i]["repo"]["url"], "^30") + "|"))
        except KeyError as err:
            print(f"<> KeyError at {i}: {err}\n    deb infos: {debs[i]}")
            _problematic_debs.append((i, debs[i]))
    
    print(("-"*total_wid))


###########################################################
###     UI / Interactions

def ui_cli_download_user_selected_debs(deb_infos, overwrite, slug_subdir, preselection=None):
    list_deb(deb_infos)
    
    # allows batch CLI without having to supervise
    if preselection is None:
        desired_deb_indexes = input(">> input no(s). of deb files to download /or/ 'all' to download them all (can take time): ").strip()
    else:
        desired_deb_indexes = preselection.strip()
        print(f">> | no(s). of deb files to download [preselection]: {desired_deb_indexes}")
    
    
    if desired_deb_indexes.lower() == "all":
        positions = range(len(deb_infos))
        print(f"Requested all {len(deb_infos)} deb files")
    else:
        positions = [try_int(pos) for pos in desired_deb_indexes.split(" ") if try_int(pos)]
    
    packagesInfos = {num: {"url":deb_infos[num]["repo"]["url"], "index":i, "pos":num, "deb":deb_infos[num], "path":savepath_for_deb(deb_infos[num]["repo"]["url"], deb_infos[num], slug_subdir)} for i, num in enumerate(positions)}
    remainingToFetch = {key:packagesInfos[key] for key in packagesInfos if overwrite or not os.path.exists(packagesInfos[key]["path"])}
    print(f"{len(remainingToFetch)} debs to fetch among the {len(deb_infos)}")
    
    _nleading_zeros = str(int(math.ceil(math.log(len(remainingToFetch), 10)))) if len(remainingToFetch) > 0 else 0
    for k, key in enumerate(remainingToFetch):
        num = remainingToFetch[key]["pos"]
        target_deb = remainingToFetch[key]["deb"]
        print((("[*] {:0"+_nleading_zeros+"}/{} downloading deb at index {}: {}").format(k+1, len(remainingToFetch), num, target_deb['Name'])))
        cydiarepoURL = remainingToFetch[key]["url"]
        
        if is_empty_deb_file_url(cydiarepoURL, target_deb):
            print(f"    Empty url for deb {target_deb['Name']}:\n    {target_deb}\n")
            if DEBUG_FLAG >= 2:
                import code
                code.interact()
            pass
        else:
            download_deb_file(cydiarepoURL, target_deb, overwrite, slug_subdir)
            print("[+] download deb done")
    pass


filepath_for_repo_source = lambda url: os.path.join(SOURCES_DIRECTORY, f"{get_repo_slugname(url)}.Packages")


###########################################################


def ArgParser():
    usage = ("[usage]: cydiarepor [--list, -s <search_string>] "
             "[cydiarepo_url, --defaultrepos] [-o] [--select]")
    
    prog = os.path.basename(os.sys.argv[0])
    parser = argparse.ArgumentParser(prog=prog,
        usage=usage,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""
        """,
        epilog=f"""
        Usage examples:
        
        # lists the packages of the repo https://build.frida.re #
        $ {prog} --listdeb https://build.frida.re
        # same as above, but prints only those containing "terminal" #
        $ {prog} --listdeb https://build.frida.re -s terminal
        
        ###   Download   ###
        # search packages containing "terminal" in the single provided repos #
        $ {prog} -s terminal  https://build.frida.re
        # same as above but searching also in all the default repos #
        $ {prog} -s terminal  https://build.frida.re --defaultrepos
        # same as above but no confirmation asked before downloading at index 3 (i.e. position 4) #
        $ {prog} -s terminal  https://build.frida.re --defaultrepos --preselection 3
        
        ###   infos   ###
        # prints default sources #
        $ {prog} --defaultrepos
        
        ### DEPRECATED ###
        # Checks for invalid deb filenames among the search results yielded #
        # by the search term <some_term>. #
        # Note: the initial issue was fixed so this option is no more useful. #
        $ {prog} --check https://build.frida.re -s <some_term>
        # check for invalid package URLs in the default repos #
        # if prog -s is not provided, it will inspect all the packages #
        $ {prog} --check -d [-s <filter_term>]
        """
        )

    
    parser.add_argument("cydiarepo_url", nargs="?", 
                help=("A custom repository you want to process. If the "
                      "command you use accepts multiple repositories, "
                      "then the one provided here will be added to those. "
                      "Otherwise (if the command only accepts 1 repo), this "
                      "repo will be the only one used."))
    
    commands_group = parser.add_argument_group("Commands")
    commands_group.add_argument("--listdeb", "-l", "--list",
                        # dest="listdeb",
                        action="store_true",
                        help="list all deb package of cydia repo")

    commands_group.add_argument("--searchstring", "--search", "-s", "--string",
                dest="searchstring",
                help=("search deb by string. You can also pass the empty "
                      "string '' to filter with the empty string."))
    
    commands_group.add_argument("--defaultrepos", "-d", "--default",
                # dest="defaultrepos",
                action="store_true",
                help="Use default repos instead of a specific one")
    
    commands_group.add_argument("--otherrepos",
                nargs="+", default=[],
                # dest="defaultrepos",
                # action="store_true",
                help=("Custom repositories. Use this option when you can "
                      "specify multiple repos and not just one."))
    
    commands_group.add_argument("--checkpackageuri", "--check",
                action="store_true",
                help="Checks the urls of (selected) packages (of selected repos) and shows invalid / missing packages.")
    
    commands_group.add_argument("--addSource", "--updateSource",
                dest="saveSource",
                action="store_true",
                help=("Add or update repository source. It will cache the "
                      "repo so that it can be reused later."))
    
    #
    parser.add_argument("--nosubdir", "--toroot", "-r",
                action="store_true",
                help=("Place downloaded debs in the root download folder "
                      "instead of sub directories"))
    
    parser.add_argument("--overwrite", "-o",
                action="store_true",
                help="Force download and overwrite existing deb files")
    
    parser.add_argument("--preselection", "--select",
                help=("Pre-selection for user choices when required. Avoids "
                      "interuptions waiting for user input. You can pass in "
                      "the index of a package to download with option -s, or "
                      "you can also use 'all' (without quotes), just like you "
                      "would do when using the script interactily."))
    
    
    parser.add_argument("--debug",
                type=int, default=0,
                help="DEBUG flag. Common people need not tangle with this.")
    
    return parser

def ParsedArgumentsValidator(args):
    if (args.listdeb or args.searchstring) and not (args.cydiarepo_url or args.defaultrepos):
        parser.error("Repository required. Either use --defaultrepos or provide a url as <cydiarepo_url>")
    
    # if args.defaultrepos and not args.cydiarepo_url:
    #     parser.error("--defaultrepos requires <cydiarepo_url>")
    
    return True


if __name__ == "__main__":          
    cydiarepoURL = ''
    parser = ArgParser()
    args = parser.parse_args()
    DEBUG_FLAG = args.debug
    valid = ParsedArgumentsValidator(args)
        
    if len(sys.argv) <= 1:
        print(parser.format_help())
        exit()
    
    repos = [args.cydiarepo_url] if args.cydiarepo_url else []
    repos += args.otherrepos
    repos += get_default_cydia_repo_array() if args.defaultrepos else []
    
    assert len(repos) >= 1, f"You should either provide a repo or use the default repos options"
    
    
    if args.saveSource:
        for url in repos:
        # url = args.cydiarepo_url
            tmp = get_raw_unarchived_packages_file_from_cydiarepoURL(url)
            raw_packages_unarchived, package_file_url, encoding = tmp
            
            filepath = filepath_for_repo_source(url)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            packages_count = -1
            try:
                if isinstance(raw_packages_unarchived, str):
                    pass
                elif encoding:
                    raw_packages_unarchived = raw_packages_unarchived.decode(encoding=encoding)
                else:
                    encodings = ['utf-8', 'iso-8859-1']
                    raw_packages_unarchived, encoding = try_decode_using_encodings(raw_packages_unarchived, encodings)
                    if encoding is None:
                        raw_packages_unarchived = raw_packages_unarchived.decode()
                
                with open(filepath, "w") as fh:
                    fh.write(raw_packages_unarchived)
                
            except UnicodeDecodeError:
                # better caching something even if it can't be decoded than nothing
                with open(filepath, "wb") as fh:
                    fh.write(raw_packages_unarchived)
                print(f"  Encoding of repo {url} could not be found. Saving as is...")
            else:
                packages = extract_raw_packages_list_from_content(raw_packages_unarchived)
                packages = list(filter(lambda p: len(p.strip()) > 0, packages))
                packages_count = len(packages)
                if len(packages) == 0:
                    print(f"  The repo {slugname} has no package. Please ensure it is configured correctly.")
            finally:
                print(f"  Saved the source file for {url} ({packages_count} packages in the repo).")
            
            
            ### Saving all cached repos in a file.
            ### It will allow the mimic of cydia's behaviour of updating
            ### all sources at once
            fp_repos = os.path.join("sources", "_repositories_.json")
            try:
                with open(fp_repos, "r") as fh:
                    repos_infos = json.load(fh)
            except FileNotFoundError:
                repos_infos = {}
            
            ## do things here to store the curent state of fetched repos
            repo_key = get_repo_slugname(url)
            
            repo_data = repos_infos.get(repo_key, {})
            packagesUrl, usesDebian = repo_data.get("packagesUrl"), repo_data.get("usesDebian")
            encoding = encoding if encoding else repo_data.get("encoding", None)
            if not packagesUrl or usesDebian is None:
                # can take time to reach out for resources so do only if needed
                packagesUrl, usesDebian = get_cydiarepo_reachable_url(url)
            
            tmp = {
                "repoRoot": url,
                "slugname": repo_key,
                "packagesCount": packages_count,
                "lastUpdate": str(datetime.datetime.today()),
                "packagesUrl": packagesUrl,
                "encoding": encoding,
                "usesDebian": usesDebian,
            }
            repo_data.update(tmp)
            repos_infos[repo_key] = repo_data
            with open(fp_repos, "w") as fh:
                json.dump(repos_infos, fh, indent=2)
        
        
    elif args.listdeb:
        all_repo_debs = []
        
        for url in repos:
            debs = get_debs_from_cydiarepo(url, False)
            filtered_debs = debs
            
            if args.searchstring is not None:
                filtered_debs = []
                for deb in debs:
                    if is_need_by_search_string(deb, args.searchstring):
                        filtered_debs.append(deb)
            
            all_repo_debs += filtered_debs
        
        list_all_repo_deb(all_repo_debs)
        # exit(0)
    
    elif args.searchstring is not None or args.checkpackageuri:
        requested_debs = []
        
        debs = get_debs_in_cydia_repos(repos)
        if args.searchstring:
            ## filtering based on search term
            for deb in debs:
                if is_need_by_search_string(deb, args.searchstring):  # and not is_malformed_deb_infos(deb):
                    requested_debs.append(deb)
        else:
            requested_debs = debs
        
        if args.checkpackageuri:
            # only check invalid urls
            print("Checking packages of repos to see if there are any invalid URLs...")
            foo_repo_url = args.cydiarepo_url if args.cydiarepo_url else repos[0]
            invalid_debs = [target_deb for target_deb in requested_debs if is_empty_deb_file_url(foo_repo_url, target_deb)]
            if invalid_debs:
                print(f"\n\n{'-' * 60}\n\n".join(map(lambda x:json.dumps(x, indent=2), invalid_debs)))
            else:
                print("No invalid debs")
        else:
            ui_cli_download_user_selected_debs(requested_debs, args.overwrite, not args.nosubdir, args.preselection)
        # exit(0)
    
    elif args.defaultrepos:
        # the user wants to print the default sources since no main action
        tmp = "".join(list(map(lambda x: f"\n  - {x}", repos)))
        print(f"Repositories:{tmp}")
    
    else:
        print("[-] you can not reach here!!!")
