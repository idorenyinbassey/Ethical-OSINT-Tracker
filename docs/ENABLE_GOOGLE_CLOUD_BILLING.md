# How to Enable Billing in Google Cloud Console

## Quick Links

- **Direct Billing Link for Your Project**: https://console.developers.google.com/billing/enable?project=654446915094
- **General Billing Console**: https://console.cloud.google.com/billing
- **Google Cloud Console**: https://console.cloud.google.com

---

## Step-by-Step Guide

### Step 1: Sign in to Google Cloud Console

1. Go to: https://console.cloud.google.com
2. Sign in with your Google account (the one associated with your API key)
3. Make sure you're viewing the correct project (#654446915094)

### Step 2: Navigate to Billing

**Option A: Direct Link (Fastest)**
- Click: https://console.developers.google.com/billing/enable?project=654446915094
- This takes you directly to the billing setup for your project

**Option B: Manual Navigation**
1. Click the hamburger menu (☰) in the top-left corner
2. Scroll down to **"Billing"**
3. Click **"Billing"** in the sidebar

### Step 3: Create or Link a Billing Account

You'll see one of these screens:

#### Scenario A: No Billing Account Exists
If you've never set up billing:

1. Click **"Create Billing Account"**
2. Choose your **Country**
3. Accept **Terms of Service**
4. Click **"Continue"**

#### Scenario B: Billing Account Exists
If you already have a billing account:

1. Click **"Link a Billing Account"**
2. Select your existing billing account from the dropdown
3. Click **"Set Account"**

### Step 4: Add Payment Method

1. You'll be prompted to enter payment information:
   - **Card Number**
   - **Expiration Date** (MM/YY)
   - **CVC** (3-digit security code)
   - **Billing Address**

2. **Important Notes**:
   - Google requires a valid credit/debit card
   - You won't be charged immediately
   - Free tier provides 1,000 Vision API requests/month
   - Only charged if you exceed free tier limits

3. Click **"Start my free trial"** or **"Submit and enable billing"**

### Step 5: Verify Billing is Enabled

1. After submitting, you'll see a confirmation message
2. Go back to your project dashboard
3. Click on **"Billing"** in the left sidebar
4. You should see:
   - ✅ Billing Account: [Your Account Name]
   - ✅ Billing Status: **Active**

### Step 6: Enable Cloud Vision API (If Not Already Enabled)

1. Go to: https://console.cloud.google.com/apis/library
2. Search for **"Cloud Vision API"**
3. Click on **"Cloud Vision API"**
4. Click **"Enable"** button (if not already enabled)
5. Wait 1-2 minutes for activation

### Step 7: Test Your API Key

Back in the OSINT Tracker app:

1. Go to **Settings** → **API Integrations**
2. Click on **"Google Cloud Vision AI"**
3. Your API key should already be saved: `AIzaSyDXH61NbSl2dpGOAb1LPf01-ElT_gnTgCc`
4. Click **"Test API Connection"**
5. Expected result: ✅ **Connection Successful! API key is valid and working.**

---

## Google Cloud Free Tier (Important!)

### Cloud Vision API - Free Tier Limits

| Feature | Free Tier (Monthly) | After Free Tier |
|---------|---------------------|-----------------|
| **OCR (Text Detection)** | 1,000 units | $1.50 per 1,000 units |
| **Label Detection** | 1,000 units | $1.50 per 1,000 units |
| **Face Detection** | 1,000 units | $1.50 per 1,000 units |
| **Web Detection** | 1,000 units | $1.50 per 1,000 units |
| **Safe Search Detection** | 1,000 units | $1.50 per 1,000 units |

**Important Notes**:
- Each image analysis counts as **1 unit per feature**
- Our app uses 5 features per image = **5 units per analysis**
- With free tier: **~200 images analyzed per month** before charges
- You can set billing alerts to avoid unexpected charges

### Setting Up Billing Alerts (Recommended)

1. Go to: https://console.cloud.google.com/billing
2. Click on your billing account
3. Click **"Budgets & alerts"** in the left sidebar
4. Click **"Create Budget"**
5. Set up alert:
   - **Name**: Vision API Budget
   - **Budget Amount**: $5 (or your preferred limit)
   - **Alert Threshold**: 50%, 90%, 100%
6. Add your email for notifications
7. Click **"Finish"**

Now you'll receive email alerts before you hit your spending limit!

---

## Troubleshooting

### Error: "Billing account is not active"

**Solution**:
1. Go to: https://console.cloud.google.com/billing
2. Check if your payment method is valid
3. Update credit card if it expired
4. Make sure billing account is **not disabled**

### Error: "This API method requires billing"

**Solution**:
1. Wait 2-3 minutes after enabling billing (propagation delay)
2. Clear browser cache
3. Generate a new API key if the old one was created before billing was enabled
4. Test again

### Error: "Payment method was declined"

**Solution**:
1. Contact your bank - they may have blocked Google charges
2. Try a different credit/debit card
3. Use a Google Pay balance (if available in your country)
4. Check if your card supports international transactions

### Error: "The card has expired"

**Solution**:
1. Go to: https://console.cloud.google.com/billing
2. Click **"Payment method"**
3. Click **"Add payment method"**
4. Enter new card details
5. Set as default payment method

### Project Not Found (#654446915094)

**Solution**:
1. Make sure you're signed in with the correct Google account
2. The API key is tied to a specific project
3. If you don't have access, you may need to:
   - Create a new project
   - Generate a new API key
   - Enable Cloud Vision API
   - Update the key in OSINT Tracker settings

---

## Creating a New Project (If Needed)

If you don't have access to project #654446915094, create your own:

### Step 1: Create New Project

1. Go to: https://console.cloud.google.com
2. Click project dropdown (top-left, next to "Google Cloud")
3. Click **"New Project"**
4. Enter:
   - **Project Name**: OSINT-Tracker (or your preferred name)
   - **Location**: No organization
5. Click **"Create"**
6. Wait 30 seconds for project creation

### Step 2: Enable Cloud Vision API

1. Go to: https://console.cloud.google.com/apis/library
2. Search for **"Cloud Vision API"**
3. Click **"Enable"**
4. Wait 1-2 minutes

### Step 3: Create API Key

1. Go to: https://console.cloud.google.com/apis/credentials
2. Click **"Create Credentials"** → **"API Key"**
3. Copy the generated key (starts with `AIza`, 39 characters)
4. (Optional) Click **"Restrict Key"**:
   - Select **"Cloud Vision API"** only
   - This improves security

### Step 4: Enable Billing (Follow Steps Above)

### Step 5: Update OSINT Tracker

1. Go to **Settings** → **API Integrations**
2. Click **"Google Cloud Vision AI"**
3. Paste your new API key
4. Click **"Test API Connection"**
5. Should show: ✅ Connection Successful!

---

## Cost Management Tips

### 1. Monitor Usage
```
Dashboard → Cloud Vision API → Quotas & Usage
```
- Check daily/weekly usage
- See which features consume most units

### 2. Set Quotas (Optional)
```
Dashboard → Cloud Vision API → Quotas
```
- Limit requests per day/minute
- Prevents accidental overage

### 3. Disable API When Not Needed
```
Settings → API Integrations → Toggle "Enable this API" OFF
```
- In OSINT Tracker app
- Prevents accidental usage

### 4. Use Metadata Extraction Only
```
Investigation → Image Recognition
```
- The built-in metadata extractor is **always free**
- Gets Device, Date Taken, Location, etc.
- Only use API when you need:
  - Face detection
  - Label/object recognition
  - OCR text extraction

---

## Support & Resources

### Google Cloud Support
- **Documentation**: https://cloud.google.com/vision/docs
- **Pricing**: https://cloud.google.com/vision/pricing
- **Support**: https://cloud.google.com/support
- **Community**: https://stackoverflow.com/questions/tagged/google-cloud-vision

### Common Questions

**Q: Will I be charged immediately?**  
A: No. You have 1,000 free requests per month. Only charged if you exceed that.

**Q: How do I cancel billing?**  
A: Go to Billing → Select account → "Close billing account". But you'll lose API access.

**Q: Can I use a debit card?**  
A: Yes, most debit cards with Visa/Mastercard logo work.

**Q: What if I exceed free tier accidentally?**  
A: Set up billing alerts (see above). Google will email you before charging.

**Q: Is my credit card information secure?**  
A: Yes. Google uses industry-standard encryption. They're PCI DSS compliant.

**Q: Can I get a refund?**  
A: Contact Google Cloud Support. They may provide credits for first-time users.

---

## Summary Checklist

- [ ] Go to: https://console.developers.google.com/billing/enable?project=654446915094
- [ ] Create or link billing account
- [ ] Add payment method (credit/debit card)
- [ ] Verify billing is **Active**
- [ ] Confirm Cloud Vision API is **Enabled**
- [ ] Test API key in OSINT Tracker: `AIzaSyDXH61NbSl2dpGOAb1LPf01-ElT_gnTgCc`
- [ ] Expected: ✅ Connection Successful!
- [ ] (Optional) Set up billing alerts ($5 budget recommended)
- [ ] (Optional) Set daily quotas to limit usage

---

## Next Steps After Enabling Billing

Once billing is enabled and tested:

1. **Upload Test Image**:
   - Go to Investigation → Image Recognition
   - Select a case
   - Upload a photo
   - Click "Analyze Image"

2. **Expected Results**:
   - ✅ Device: Camera model
   - ✅ Date Taken: Photo timestamp
   - ✅ Faces Detected: Number of faces
   - ✅ Labels: Objects in image (person, indoor, etc.)
   - ✅ OCR Text: Any text in the image
   - ✅ Safe Search: Content safety ratings

3. **Metadata Display**:
   - Click "Complete Metadata (26+ fields)" to expand
   - See all EXIF data + API results

---

**Need Help?**  
- Check the app logs in terminal
- Review error messages in Settings → Test API Connection
- See `GOOGLE_VISION_API_FIX_PLAN.md` for troubleshooting

**Estimated Time**: 5-10 minutes  
**Cost**: Free for first 1,000 requests/month  
**Result**: Fully functional image recognition with face detection, OCR, and labels! 🎉
