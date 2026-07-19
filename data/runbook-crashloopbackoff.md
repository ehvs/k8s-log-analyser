# Runbook: Pod em CrashLoopBackOff

## Sintoma
Um pod reinicia repetidamente e fica no estado `CrashLoopBackOff`.

## Diagnóstico
1. `kubectl describe pod <pod>` — verifique os Events e o motivo do último término.
2. `kubectl logs <pod> --previous` — veja os logs da instância anterior que crashou.
3. Confira `readinessProbe`/`livenessProbe`: probes agressivas demais podem matar o pod antes de ele subir.
4. Verifique limites de recursos: OOMKilled indica memória insuficiente.

## Causas comuns
- Erro de configuração (variável de ambiente ou secret ausente).
- Dependência indisponível no start (banco, fila).
- `command`/`args` incorretos na imagem.
- Memória insuficiente (OOMKilled) — aumente `resources.limits.memory`.

## Resolução
- Corrija a config e faça `kubectl rollout restart deployment/<nome>`.
- Se for probe, aumente `initialDelaySeconds`.
- Se for OOM, ajuste os limites de memória.
