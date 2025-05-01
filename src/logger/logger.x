struct log_entry {
    string username<255>;
    string operation<64>;
    string filename<255>;
    string timestamp<64>;
};

program LOGGER_PROG {
    version LOGGER_VERS {
        void LOG_OP(log_entry) = 1;
    } = 1;
} = 0x20000001;