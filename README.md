# 🚀 SocRadar Entra ID Sync Function

This Azure Function automatically fetches security and audit logs from Microsoft Entra ID (via Microsoft Graph) using the secure Client Credentials Flow (Service Principal) and pushes them to the SocRadar ingestion API.

## Prerequisites

1.  **Azure Entra ID App Registration:**
    * Create an App Registration and save the **Tenant ID**, **Client ID**, and a **Client Secret**.
    * Grant **Application Permissions** to the App (e.g., `AuditLog.Read.All`) and grant **Admin Consent**.
2.  **SocRadar API Key:** Obtain your data ingestion URL and API Key from SocRadar.

---

## ⚙️ Deployment Steps

### 1. Deploy Azure Infrastructure (One-Click)

The button below will deploy the necessary Azure resources (Function App, Storage Account, Application Insights) using the provided ARM template.

[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https://raw.githubusercontent.com/Radargoger/socradar-entra-app/main/host.json)

**⚠️ Important:** During deployment, you must provide your saved **Client ID**, **Client Secret**, **Tenant ID**, and **SocRadar API Key** into the form fields.

### 2. Configure Continuous Deployment (CD)

After the infrastructure deployment is complete:

Your Function App is created, but it needs to pull the code from this GitHub repository.

1.  Navigate to your newly created **Function App** in the Azure Portal.
2.  Go to **Deployment Center**.
3.  Select **GitHub** as the source.
4.  Authorize your account and select this repository: `Radargoger/socradar-entra-app`.
5.  Save the settings to trigger the first deployment. Azure will automatically pull your Python code and install the dependencies (`requests`).

### 3. Verification

Once the deployment is finished, the function will run every 5 minutes (as configured in `function.json`), fetch data from Entra ID, and push it to SocRadar. You can monitor the logs in **Application Insights**.
