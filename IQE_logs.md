baa@brdinterop6331:~$ kubectl logs -f baxter-bullseye-siteconfiguration-646bc9d9d7-w4nnk -n ns
Defaulted container "baxter-bullseye-siteconfiguration" out of: baxter-bullseye-siteconfiguration, download-user-manuals-and-language-pack (init)
cp: can't stat '/app/clientapp/config/init_locales/*.json': No such file or directory
ls: /app/clientapp/site-configuration/public/config/usermanuals/IQ*.pdf: No such file or directory
Unable to find the user manuals in /app/clientapp/public/config/usermanuals/
/app/clientapp/site-configuration/config/locales/en-US.json
/app/clientapp/site-configuration/config/locales/es-CO.json
/app/clientapp/site-configuration/config/locales/es-DO.json
/app/clientapp/site-configuration/config/locales/es-LA.json
/app/clientapp/site-configuration/config/locales/es-MX.json
/app/clientapp/site-configuration/config/locales/fr-BE.json
/app/clientapp/site-configuration/config/locales/fr-CA.json
/app/clientapp/site-configuration/config/locales/fr-CH.json
/app/clientapp/site-configuration/config/locales/fr-FR.json
/app/clientapp/site-configuration/config/locales/fr.json
/app/clientapp/site-configuration/config/locales/pt-BR.json
/app/clientapp/site-configuration/config/locales/pt-PT.json
/app/clientapp/site-configuration/config/locales/pt.json
warn: Microsoft.AspNetCore.DataProtection.Repositories.FileSystemXmlRepository[60]
      Storing keys in a directory '/app/.aspnet/DataProtection-Keys' that may not be persisted outside of the container. Protected data will be unavailable when container is destroyed. For more information go to https://aka.ms/aspnet/dataprotectionwarning
warn: Microsoft.AspNetCore.DataProtection.KeyManagement.XmlKeyManager[35]
      No XML encryptor configured. Key {46f3d189-d403-4e81-ad6d-6371185e30ef} may be persisted to storage in unencrypted form.
warn: Microsoft.AspNetCore.Hosting.Diagnostics[15]
      Overriding HTTP_PORTS '8080' and HTTPS_PORTS ''. Binding to values defined by URLS instead 'https://+:443'.
info: Microsoft.Hosting.Lifetime[14]
      Now listening on: https://[::]:443
info: Microsoft.Hosting.Lifetime[0]
      Application started. Press Ctrl+C to shut down.
info: Microsoft.Hosting.Lifetime[0]
      Hosting environment: Production
info: Microsoft.Hosting.Lifetime[0]
      Content root path: /app
fail: Baxter.Bullseye.SiteConfiguration.Services.EapTlsLibraryService[0]
      ObtainRootCertificate :: Failed to obtain root certificate. Failed to execute openssl command to convert root certificate (DER) to PEM format.
      Logs: unable to load PKCS7 object

      .

fail: Baxter.Bullseye.SiteConfiguration.Services.EapTlsLibraryService[0]
      ObtainRootCertificate :: Failed to obtain root certificate. Failed to execute openssl command to convert root certificate (DER) to PEM format.
      Logs: unable to load PKCS7 object

      .

fail: Baxter.Bullseye.SiteConfiguration.Services.EapTlsLibraryService[0]
      ObtainRootCertificate :: Failed to obtain root certificate. Failed to execute openssl command to convert root certificate (DER) to PEM format.
      Logs: unable to load PKCS7 object

      .

fail: Baxter.Bullseye.SiteConfiguration.Services.EapTlsLibraryService[0]
      ObtainRootCertificate :: Failed to obtain root certificate. Failed to execute openssl command to convert root certificate (DER) to PEM format.
      Logs: unable to load PKCS7 object

      .

fail: Baxter.Bullseye.SiteConfiguration.Services.EapTlsLibraryService[0]
      ObtainRootCertificate :: Failed to obtain root certificate. Failed to execute openssl command to convert root certificate (DER) to PEM format.
      Logs: unable to load PKCS7 object

      .

fail: Baxter.Bullseye.SiteConfiguration.Services.EapTlsLibraryService[0]
      ObtainRootCertificate :: Failed to obtain root certificate. Failed to execute openssl command to convert root certificate (DER) to PEM format.
      Logs: unable to load PKCS7 object

      .

fail: Baxter.Bullseye.SiteConfiguration.Services.EapTlsLibraryService[0]
      ObtainRootCertificate :: Failed to obtain root certificate. Failed to execute openssl command to convert root certificate (DER) to PEM format.
      Logs: unable to load PKCS7 object

      .

fail: Baxter.Bullseye.SiteConfiguration.Services.EapTlsLibraryService[0]
      ObtainRootCertificate :: Failed to obtain root certificate. Invalid Parameter - Value of Registration Authority certificate file cannot be null or empty.
fail: Baxter.Bullseye.SiteConfiguration.Services.EapTlsLibraryService[0]
      ObtainRootCertificate :: Failed to obtain root certificate. Invalid Parameter - Value of Registration Authority certificate file cannot be null or empty.
fail: Baxter.Bullseye.SiteConfiguration.Services.EapTlsLibraryService[0]
      ObtainRootCertificate :: Failed to obtain root certificate. Invalid Parameter - Value of Registration Authority certificate file cannot be null or empty.
fail: Baxter.Bullseye.SiteConfiguration.Services.EapTlsLibraryService[0]
      ObtainRootCertificate :: Failed to obtain root certificate. Invalid Parameter - Value of Registration Authority certificate file cannot be null or empty.
fail: Baxter.Bullseye.SiteConfiguration.Services.EapTlsLibraryService[0]
      ObtainRootCertificate :: Failed to obtain root certificate. Invalid Parameter - Value of Registration Authority certificate file cannot be null or empty.
fail: Baxter.Bullseye.SiteConfiguration.Services.EapTlsLibraryService[0]
      ObtainRootCertificate :: Failed to obtain root certificate. Invalid Parameter - Value of Registration Authority certificate file cannot be null or empty.
fail: Baxter.Bullseye.SiteConfiguration.Services.EapTlsLibraryService[0]
      ObtainRootCertificate :: Failed to obtain root certificate. Invalid Parameter - Value of Registration Authority certificate file cannot be null or empty.
fail: Baxter.Bullseye.SiteConfiguration.Services.EapTlsLibraryService[0]
      ObtainRootCertificate :: Failed to obtain root certificate. Invalid Parameter - Value of Registration Authority certificate file cannot be null or empty.
fail: Baxter.Bullseye.SiteConfiguration.Services.EapTlsLibraryService[0]
      ObtainRootCertificate :: Failed to obtain root certificate. Invalid Parameter - Value of Registration Authority certificate file cannot be null or empty.
fail: Baxter.Bullseye.SiteConfiguration.Services.EapTlsLibraryService[0]
      ObtainRootCertificate :: Failed to obtain root certificate. Invalid Parameter - Value of Registration Authority certificate file cannot be null or empty.
fail: Baxter.Bullseye.SiteConfiguration.Services.EapTlsLibraryService[0]
      ObtainRootCertificate :: Failed to obtain root certificate. Invalid Parameter - Value of Registration Authority certificate file cannot be null or empty.
fail: Baxter.Bullseye.SiteConfiguration.Services.EapTlsLibraryService[0]
      ObtainRootCertificate :: Failed to obtain root certificate. Invalid Parameter - Value of Registration Authority certificate file cannot be null or empty.
fail: Baxter.Bullseye.SiteConfiguration.Services.EapTlsLibraryService[0]
      ObtainRootCertificate :: Failed to obtain root certificate. Invalid Parameter - Value of Registration Authority certificate file cannot be null or empty.
fail: Baxter.Bullseye.SiteConfiguration.Services.EapTlsLibraryService[0]
      ObtainRootCertificate :: Failed to obtain root certificate. Invalid Parameter - Value of Registration Authority certificate file cannot be null or empty.
fail: Baxter.Bullseye.SiteConfiguration.Services.EapTlsLibraryService[0]
      ObtainRootCertificate :: Failed to obtain root certificate. Invalid Parameter - Value of Registration Authority certificate file cannot be null or empty.
fail: Baxter.Bullseye.SiteConfiguration.Services.EapTlsLibraryService[0]
      ObtainRootCertificate :: Failed to obtain root certificate. Invalid Parameter - Value of Registration Authority certificate file cannot be null or empty.
fail: Baxter.Bullseye.SiteConfiguration.Services.EapTlsLibraryService[0]
      ObtainRootCertificate :: Failed to obtain root certificate. Invalid Parameter - Value of Registration Authority certificate file cannot be null or empty.
fail: Baxter.Bullseye.SiteConfiguration.Services.EapTlsLibraryService[0]
      ObtainRootCertificate :: Failed to obtain root certificate. Invalid Parameter - Value of Registration Authority certificate file cannot be null or empty.
fail: Baxter.Bullseye.SiteConfiguration.Services.EapTlsLibraryService[0]
      ObtainRootCertificate :: Failed to obtain root certificate. Failed to execute openssl command to convert root certificate (DER) to PEM format.
      Logs: unable to load PKCS7 object

      .

fail: Baxter.Bullseye.SiteConfiguration.Services.EapTlsLibraryService[0]
      ObtainRootCertificate :: Failed to obtain root certificate. Failed to execute openssl command to convert root certificate (DER) to PEM format.
      Logs: unable to load PKCS7 object

      .

fail: Baxter.Bullseye.SiteConfiguration.Services.EapTlsLibraryService[0]
      ObtainRootCertificate :: Failed to obtain root certificate. Failed to execute openssl command to convert root certificate (DER) to PEM format.
      Logs: unable to load PKCS7 object

      .

fail: Baxter.Bullseye.SiteConfiguration.Services.EapTlsLibraryService[0]
      ObtainRootCertificate :: Failed to obtain root certificate. Failed to execute openssl command to convert root certificate (DER) to PEM format.
      Logs: unable to load PKCS7 object

      .

fail: Baxter.Bullseye.SiteConfiguration.Services.EapTlsLibraryService[0]
      ObtainRootCertificate :: Failed to obtain root certificate. Failed to execute openssl command to convert root certificate (DER) to PEM format.
      Logs: unable to load PKCS7 object

      .

fail: Baxter.Bullseye.SiteConfiguration.Services.EapTlsLibraryService[0]
      ObtainRootCertificate :: Failed to obtain root certificate. Failed to execute openssl command to convert root certificate (DER) to PEM format.
      Logs: unable to load PKCS7 object

      .

fail: Baxter.Bullseye.SiteConfiguration.Services.EapTlsLibraryService[0]
      ObtainRootCertificate :: Failed to obtain root certificate. Failed to execute openssl command to convert root certificate (DER) to PEM format.
      Logs: unable to load PKCS7 object

      .

fail: Baxter.Bullseye.SiteConfiguration.Services.EapTlsLibraryService[0]
      ObtainRootCertificate :: Failed to obtain root certificate. Failed to execute openssl command to convert root certificate (DER) to PEM format.
      Logs: unable to load PKCS7 object