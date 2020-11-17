# Documentation on the do-release script

The do-release.pl script copies distributions from the temporary holding area
to the http and ftp areas. It it intended to be run as the `openssl` user on
dev.openssl.org.

It does the following:

1. Copy OpenSSL release files from the holding area to the http and ftp
   locations: currently /v/openssl/www/source and /v/openssl/ftp/source
2. Move OpenSSL release files from holding area to ~openssl/dist/old By
   doing this the script wont try and make a release again with old files.
3. Mail the release message. This is sent to openssl-project openssl-users
   and openssl-announce (it needs to be approved in openssl-announce). The
   subject line is `OpenSSL version xxx released`.

## do-release options

- `--copy`<br>
  Copy files to http and ftp directories.  **You will have to manually move
  the OLD files to old/<SUBDIR> directories.**

- `--move`<br>
  Move files from holding area to ~openssl/dist/old

- `--mail`<br>
  Send out announcement email: if this option is not given, the command you
  need to call to send the release mail will be printed out.

- `--full-release`<br>
  Perform all operations for a release (copy, move and mail).

Note: because several of these options are irreversible they have to be
explicitly included.
