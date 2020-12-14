This code needs you to create an app on Microsoft Azure :
- Go to https://portal.azure.com and log in with your address.
- Go to Azure Active Directory -> Apps registration -> New registration
- Choose "Accounts in any organizational directory (Any Azure AD directory - Multitenant) and personal Microsoft
  accounts (e.g. Skype, Xbox)" and your "Redirect URI" ex: http://localhost:XXXX/my_app or https if not local.
- Overview : Gives your client_id
- Authentication : To add new redirect URIs
- Certificates & secrets : Gives your client_secret (keep the value at creation, it's invisible after).
- API permissions : Determine the scopes allowed (see https://docs.microsoft.com/fr-fr/graph/permissions-reference)
See for more infos:
-> https://docs.microsoft.com/fr-fr/outlook/rest/get-started
-> https://docs.microsoft.com/fr-fr/previous-versions/office/office-365-api/api/version-2.0/calendar-rest-operations#
get-events