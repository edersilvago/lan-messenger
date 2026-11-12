@echo off
REM Libera o LAN Messenger no Firewall do Windows (perfil Dominio/Privado)
netsh advfirewall firewall add rule name="LANMsg UDP Discovery" dir=in action=allow protocol=UDP localport=50000
netsh advfirewall firewall add rule name="LANMsg TCP Chat" dir=in action=allow protocol=TCP localport=50001
netsh advfirewall firewall add rule name="LANMsg TCP Files" dir=in action=allow protocol=TCP localport=50002
echo Regras aplicadas. Pressione qualquer tecla...
pause >nul
