# Udemy Course Downloader

## Usage
```bash
$ python downloader.py --help
```

```
usage: downloader.py [-h] [-d] [-w WORDS] token

Udemy Course Downloader

positional arguments:
  token                 Udemy "access_token" cookie

options:
  -h, --help            show this help message and exit
  -d, --debug           Enable debug output
  -w WORDS, --words WORDS
                        Keywords to search for the course to download
```

If you don't use -w, the script will ask you which course to download based on the courses you are subscribed to.

If you use -w every word you type will be used to search for the course you want to download among the courses you are subscribed to.

### Example

```bash
$ python downloader.py <token> -w python with examples
```

```
Courses:
    - Python from 0 to 100 (python:OK, with:NO, examples:NO)
    - JS with examples (python:NO, with:OK, examples:OK)
    - Python with examples and more (python:OK, with:OK, examples:OK)

Selected course:
    Python with examples and more
```

## Support me
Cardano (ADA): [addr1q8zed0agtx9w4zs6335lrmfv2ehj7yydps3v7kz3c7dx9vzapmepcz9sr46k0kuct8aetwznaxlcw5yjlvf4pqfgexusfq9agd](https://cardanoscan.io/address/013501158d71cb447e20af1537893735596ca8a1a71cb9af2632bb71285d0ef21c08b01d7567db9859fb95b853e9bf875092fb13508128c9b9)

⚠ All tokens will be staked in pools that use their rewards for the benefit of nature and the environment.