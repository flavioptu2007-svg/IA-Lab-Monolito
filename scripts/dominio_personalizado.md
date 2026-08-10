# 🌐 Guia: Domínio Personalizado para o Portal Educacional (EducacionAI)

> **Status:** pendente — o portal está no ar no domínio gratuito `https://jogos-5f131.web.app`.
> Este guia fica pronto para quando você decidir registrar `educacionai.com.br`.

---

## Resumo da investigação (09/08/2026)

| Domínio | Status | Observação |
|---|---|---|
| **`educacionai.com.br`** | ✅ **Disponível** | Livre para registro no registro.br |
| `educacion-ai.com.br` | ✅ Disponível | Alternativa com hífen |
| `educacionai.com` | ❌ Ocupado | Registrado por terceiros (em "parking") desde 03/2025 |

---

## Etapa 1 — Registrar o domínio (só você pode fazer)

`.com.br` é registrado **exclusivamente no registro.br** (ou registrar credenciado). Custo: **~R$ 90/ano** (valor oficial do registro.br).

1. Acesse **https://registro.br** e crie uma conta (ou faça login).
2. Confirme o **CPF** do titular (ou CNPJ da escola, se preferir registrar no nome da instituição).
3. Busque `educacionai.com.br` → clique em **"Registrar"** → pague via boleto/PIX/cartão.
4. Após o pagamento, o domínio fica ativo em minutos/horas.
5. **Dica:** na hora de registrar, já configure os **nameservers padrão do registro.br** (`a.dns.br`, `b.dns.br`, `c.dns.br`, `dnsb...`) OU use o painel de DNS do próprio registro.br — o gerenciamento de DNS vem junto de graça.

> ⏳ Custo anual de manutenção: ~R$ 90/ano. Não deixe expirar (30 dias após o vencimento ele entra em suspensão).

---

## Etapa 2 — Adicionar o domínio no Firebase Hosting

O Firebase CLI 15 **removeu o comando** `hosting:add`/`hosting:domain` — a configuração de domínio personalizado hoje é feita **pelo console web**:

1. Acesse **https://console.firebase.google.com** → projeto **EducacionAI** (`jogos-5f131`).
2. Menu **Hosting** → aba **Domínios personalizados** → **Adicionar domínio**.
3. Digite `educacionai.com.br` (e, se quiser, `www.educacionai.com.br`).
4. O console exibe os **registros DNS exatos** que você precisa criar — guarde-os (TXT + A/CNAME).

> ✅ Domínio personalizado funciona no **plano gratuito (Spark)** — sem custo extra do Firebase.
> 🔐 O HTTPS/SSL é emitido automaticamente pelo Firebase (Let's Encrypt) — sem custo.

---

## Etapa 3 — Criar os registros DNS no registro.br

No painel do registro.br (menu **DNS / Zona DNS**), crie os registros que o console do Firebase mostrar. Eles seguem este padrão:

| Tipo | Nome | Valor | Finalidade |
|---|---|---|---|
| **TXT** | `educacionai.com.br` | `google-site-verification=<código do console>` | Verificar propriedade |
| **A** | `educacionai.com.br` | `151.101.1.195` | Aponta o domínio raiz pro Firebase |
| **A** | `educacionai.com.br` | `151.101.65.195` | (2º IP anycast, redundância) |
| **CNAME** | `www` | `jogos-5f131.web.app` | Redireciona www → site |

> ⚠️ **Sempre use os valores que o console do Firebase mostrar** — os IPs acima são os padrões, mas o console pode gerar valores específicos por domínio. Se aparecer TXT de verificação, ele é obrigatório antes dos A/CNAME.

---

## Etapa 4 — Verificação automática

1. Salve os registros no registro.br (propagação: minutos a ~1h).
2. No console Firebase, a coluna do domínio muda para **"Aguardando verificação"** → **"Ativo"** (SSL emitido em até ~30 min).
3. Confirme daqui do terminal:

```bash
dig +short educacionai.com.br
dig +short www.educacionai.com.br
curl -I https://educacionai.com.br
```

---

## Etapa 5 — (Opcional) Melhorias

- **Redirecionar `www` → raiz** (ou o contrário): configurável no console Firebase (aba Domínios).
- **E-mail no domínio:** o registro.br oferece **redirecionamento de e-mail gratuito** (ex.: `contato@educacionai.com.br` → seu Gmail).
- **Subdomínios extras:** `api.educacionai.com.br` para a API no Cloud Run (quando ela estiver no ar).

---

## Links úteis

- Registro de domínio: https://registro.br
- Console Firebase: https://console.firebase.google.com
- Deploy do portal (após atualizações): `./scripts/deploy_portal_firebase.sh`
