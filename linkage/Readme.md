# Identifying Information Bloom Filter Scrambling Windows OS Utility

## Creating the Windows OS Executable
1. [Download and install](https://www.python.org/downloads/windows/) python on windows.  Be sure to select "Customize Installation" and ensure both that pip is installed and that python is added to the windows environment variables.
1. Using the windows command terminal (type `cmd` in the windows search box) run `pip install pyinstaller`
1. In the command terminal, compile the python executable using `pyinstaller --onefile --noconsole FILE_NAME.py`.  This should create a Windows executable `.exe` file.


## Signing the Executable

Unless the windows executable is signed using a valid code signing certificate, it will be flagged as a possible virus by the Windows operating system.  [Digicert](http://digicert.com) is the current certificate provider and the procedure below works with certificates provided through their [KeyLocker](https://docs.digicert.com/en/digicert-keylocker.html) service.  Due to technical issues with the Digicert Windows code signing tools, the following procedure describes how to sign the Windows executable using tools running on Mac OS.

1. Log into the Digicert One account, navigate to KeyLocker and click on the "Get Started" wizard.
1. Create an API token and save it in a secure location.
1. Create a client authetication certificate.  Save the password in a secure location and download the certificate `.p12` file.
1. Due to problems encountered with the Click to Sign product line, the following instructions use the `smctl` command line suite provided by Digicert.  Download the Mac OS version of these tools by clicking on the Resources tab in the Digicert One account.
1. `smctl` does not actually sign an executable file with the Digicert certificate.  It needs to integrate into other third party tool suites to do this.  The [jsign](https://docs.digicert.com/en/software-trust-manager/sign-with-digicert-signing-tools/third-party-signing-tool-integrations/jsign.html) has the capability to sign Windows executables even while running on Mac OS.  Download the jsign `.jar` file.
1. Create a `pkcs11properties.cfg` file as [described here](https://docs.digicert.com/en/software-trust-manager/tools/cryptographic-libraries-and-frameworks/pkcs11-library.html) and ensure it points to the `smpkcs11.dylib` file downoaded with the Mac OS `smctl` tools.
1. Use the recommended option of storing the API key and certificate password [in the Mac OS Keychain](https://docs.digicert.com/en/software-trust-manager/general/secure-credentials/set-up-secure-credentials-for-apple/keychain-access.html).  Don't forget to set the path variables and restart the shell.
1. Check the configuration using `smctl healthcheck`.  You should see no errors.  There may not be any tools showing up under signing tools but we won't use `smctl` to actually sign the executable so that's ok.
1. Type `smctl keypair list` and take note of the key alias for use in the next step.
1. Sign the executable using the command
```
java -jar jsign-5.0.jar --keystore ./pkcs11properties.cfg --storepass changeit --storetype PKCS11 --alias <key alias> <executable>
```
1. You can verify the signing operation by right clicking on the signed executable under Windows, selecting Properties and confiriming that digital signature information is present.
