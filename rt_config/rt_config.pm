# THIS CONFIG IS FOR DEVELOPMENT USE ONLY!
Set($DatabaseType, "SQLite");
Set($DatabaseName, "/data/rt5-dev.sqlite");

Set($rtname, "DEV");
Set($WebDomain, "localhost");
Set($WebPort, 8892);
Set($WebPath, "");

Set($SendmailPath, "/bin/true");
Set($MailCommand, "sendmail");

Set($LogToSTDERR, "debug");
Set($WebSessionClass, "Apache::Session::File");
Set($WebSessionDir, "/tmp/rt5-session");

1;
