To test the new features, follow these steps:

1. Start the Django Server & Bot
Open two terminal windows in d:\israinsols_pipeline:

Terminal 1 (Django): python manage.py runserver
Terminal 2 (Bot): python manage.py run_bot
2. Add some FAQs (Testing the Dynamic Admin)
Go to the Django Admin FAQ page.
Click "Add FAQ" and create 2-3 test questions:
Q: What services do you offer? | A: We offer Web Dev, SEO, and Design!
Q: Do you provide support? | A: Yes, 24/7 premium support.
Optional: Add more than 5 FAQs to test the Pagination (Next/Previous buttons).
3. Interact with the Bot on Telegram
Open your bot on Telegram and send /start.
Test FAQs:
Click ❓ FAQs. You should see the questions you just added.
Click a question to see the answer.
Test the "Back to FAQs" button.
Test Lead Generation (Contact Us):
Click 📞 Contact Us.
The bot will ask for your Name, then Contact Info, and finally your Project Details.
After you finish, the bot should send you a confirmation.
4. Verify the Results
Check Leads: Go to the Agency Leads page in Django Admin. Your test entry should be there!
Check Notifications: If your TELEGRAM_CHAT_ID is set correctly in .env, the bot should have also sent an alert about the new lead to your admin chat.
Pro Tip: You can update an FAQ answer in the Admin and click it again in the bot to see it change instantly (or wait up to 5 minutes for the cache to refresh)!