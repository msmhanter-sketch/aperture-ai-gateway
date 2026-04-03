use anchor_lang::prelude::*;

// Твой уникальный адрес контракта в Devnet
declare_id!("C2q9yxux7b7bxFF64pkZUV6g2Vcs2bQ1FS4GUQy512wv");

#[program]
pub mod aperture_gateway {
    use super::*;

    // Инициализация канала стриминга юзером
    pub fn open_channel(ctx: Context<OpenChannel>, initial_deposit: u64) -> Result<()> {
        let channel = &mut ctx.accounts.channel;
        channel.user = *ctx.accounts.user.key;
        channel.balance = initial_deposit;
        channel.burn_rate = 0; // Изначально плата 0
        channel.last_update_time = Clock::get()?.unix_timestamp;
        
        msg!("Aperture: Channel opened. Deposit: {} USDC", initial_deposit);
        Ok(())
    }

    // ИИ-агент обновляет цену (Burn Rate) в зависимости от нагрузки
    pub fn update_burn_rate(ctx: Context<UpdateBurnRate>, new_rate: u64) -> Result<()> {
        let channel = &mut ctx.accounts.channel;
        let current_time = Clock::get()?.unix_timestamp;
        
        // Списываем токены за прошедшее время по старой цене
        let time_passed = (current_time - channel.last_update_time) as u64;
        let burned_amount = time_passed * channel.burn_rate;
        
        if channel.balance >= burned_amount {
            channel.balance -= burned_amount;
        } else {
            channel.balance = 0; // Защита от ухода в минус
        }

        // Устанавливаем новую цену, продиктованную ИИ
        channel.burn_rate = new_rate;
        channel.last_update_time = current_time;
        
        msg!("Aperture: AI updated burn rate to {} per sec", new_rate);
        Ok(())
    }
}

// Структуры аккаунтов
#[derive(Accounts)]
pub struct OpenChannel<'info> {
    #[account(init, payer = user, space = 8 + 32 + 8 + 8 + 8)]
    pub channel: Account<'info, ChannelState>,
    #[account(mut)]
    pub user: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct UpdateBurnRate<'info> {
    #[account(mut)]
    pub channel: Account<'info, ChannelState>,
    // В MVP разрешаем подписывать любому кошельку бэкенда
    pub ai_agent: Signer<'info>, 
}

#[account]
pub struct ChannelState {
    pub user: Pubkey,
    pub balance: u64,
    pub burn_rate: u64,
    pub last_update_time: i64,
}